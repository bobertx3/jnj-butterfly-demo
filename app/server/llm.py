"""
Generate Next Best Action and email draft using Databricks Foundation Model API.
Uses contact context (role, institution, signals) and J&J MedTech terminology
(Ethicon, J&J Vision, OTTAVA, Abiomed) for personalized, portfolio-aligned copy.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .config import (
    DATABRICKS_FM_ENDPOINT,
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    has_databricks_llm_credentials,
)
from .databricks_auth import get_oauth_token, get_workspace_host


def _contact_context_str(contact: dict[str, Any]) -> str:
    """Build a short context string for the LLM from contact fields."""
    parts = [
        f"Name: {contact.get('name', 'HCP')}",
        f"Role/Specialty: {contact.get('role_specialty') or 'Healthcare professional'}",
        f"Institution: {contact.get('institution') or 'Unknown'}",
        f"Priority score: {contact.get('priority_score', 0)}",
        f"Risk level: {contact.get('risk_level', 'Medium')}",
        f"Intent score: {contact.get('intent_score', 0)}",
        f"Last touch: {contact.get('last_touch_days', 0)} days ago",
        f"Preferred channel: {contact.get('preferred_channel') or 'Email'}",
    ]
    if contact.get("trx_volume_3m") is not None:
        parts.append(f"3M TRX volume: {contact['trx_volume_3m']}")
    if contact.get("nrx_volume_3m") is not None:
        parts.append(f"3M NRX volume: {contact['nrx_volume_3m']}")
    if contact.get("rx_growth_3m_pct") is not None:
        parts.append(f"3M RX growth: {contact['rx_growth_3m_pct']}%")
    if contact.get("last_interaction_channel"):
        parts.append(f"Last interaction channel: {contact['last_interaction_channel']}")
    if contact.get("last_interaction_date"):
        parts.append(f"Last interaction date: {contact['last_interaction_date']}")
    if contact.get("last_interaction_summary"):
        parts.append(f"Last interaction summary: {contact['last_interaction_summary']}")
    if contact.get("last_products_discussed"):
        parts.append(f"Last products discussed: {contact['last_products_discussed']}")
    if contact.get("next_follow_up_objective"):
        parts.append(f"Next follow-up objective: {contact['next_follow_up_objective']}")
    return "\n".join(parts)


def _build_nba_prompt(contact: dict[str, Any]) -> str:
    return f"""You are a J&J MedTech (Johnson & Johnson MedTech) field rep assistant. Our portfolios include:
- Ethicon: surgical stapling, wound closure, energy (HARMONIC, MEGADYNE), ECHELON, STRATAFIX
- J&J Vision: IOLs, refractive (TECNIS SYMFONY, ELITA), contact lenses (ACUVUE OASYS, ACUVUE VITA)
- OTTAVA: robotic surgery system
- Abiomed: heart recovery, Impella (Impella CP, Impella 5.5)

Given this HCP in the prioritized contact queue:

{_contact_context_str(contact)}

Generate a concise Next Best Action (one short paragraph, 2–3 sentences) that:
1. Is specific to their role and institution (surgical, vision, or cardiac as relevant).
2. Recommends a concrete step (e.g. 15-min check-in, product demo, clinical resource share, adoption support).
3. Mentions at least one relevant J&J MedTech portfolio or product line where appropriate.
4. If prior interaction context is provided, reference it and build on it (avoid repeating generic outreach copy).

Output ONLY the recommendation paragraph, no labels or bullet points."""


def _build_email_prompt(contact: dict[str, Any]) -> str:
    return f"""You are a senior J&J MedTech (Johnson & Johnson MedTech) field rep drafting a personalized, professional outreach email to an HCP. Our portfolios include Ethicon (surgical), J&J Vision (IOLs, refractive, contact lenses), OTTAVA (robotic surgery), and Abiomed (heart recovery, Impella).

Contact context:
{_contact_context_str(contact)}

Write a substantive outreach email that:
1. Opens with a personalized line that references their specific role, specialty, and institution by name.
2. In a second paragraph, adds clear value: mention 1–2 relevant J&J MedTech products or programs (Ethicon, J&J Vision, OTTAVA, or Abiomed) that fit their profile, and why a touchpoint would help them (e.g. clinical resources, adoption support, case discussion).
3. Closes with a specific, low-friction ask (e.g. 15-minute check-in, clinical resource share, or demo) and a sentence that makes it easy to say yes.
4. Is professional, compliant, and 2–3 short paragraphs long (roughly 80–150 words for the body). No promises or off-label language.
5. If prior interaction context exists, reference the prior discussion naturally and continue that thread.

You must output exactly in this format:
LINE 1: The email subject line only (compelling, specific; no prefix like "Subject:").
LINE 2: The exact text "BODY:"
LINE 3 and following: The full email body in 2–3 short paragraphs. Use the HCP's name and institution. Write in a warm, expert tone.

Example format:
Re: Quick 15-min check-in – [Institution] and [relevant portfolio]
BODY:
Dr. [Name], given your focus on [specialty] at [Institution], I wanted to reach out personally.

[Second paragraph: 1–2 sentences on relevant portfolio and value – e.g. clinical resources, adoption support, or program that fits their practice.]

I’d value a brief 15-minute check-in to share [specific resource or next step]. Would you have time for a call this week or next?
"""


def _parse_email_response(text: str) -> tuple[str, str]:
    """Parse subject and body from model output. Expects 'BODY:' on its own line."""
    subject = ""
    body = ""
    if "BODY:" in text:
        parts = text.split("BODY:", 1)
        first = (parts[0] or "").strip()
        lines = [l.strip() for l in first.split("\n") if l.strip()]
        subject = lines[0] if lines else "J&J MedTech – follow-up"
        body = (parts[1] or "").strip()
    else:
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        subject = lines[0] if lines else "J&J MedTech – follow-up"
        body = "\n".join(lines[1:]) if len(lines) > 1 else text.strip()
    if not subject:
        subject = "J&J MedTech – 15-min check-in this week?"
    if not body:
        body = "I'm reaching out to schedule a brief check-in to share clinical resources and adoption support."
    return subject[:256], body[:6000]


logger = logging.getLogger(__name__)


def _get_llm_token() -> Optional[str]:
    """Token for Foundation Model API: env first, then OAuth (e.g. in Databricks Apps)."""
    if DATABRICKS_TOKEN:
        return DATABRICKS_TOKEN
    return get_oauth_token()


def _call_databricks_chat(messages: list[dict[str, str]], max_tokens: int = 1024) -> Optional[str]:
    """Call Databricks Foundation Model API; returns assistant content or None on failure."""
    if not has_databricks_llm_credentials():
        return None
    token = _get_llm_token()
    host = get_workspace_host()
    if not token or not host:
        return None

    # 1) Try Databricks SDK (serving_endpoints.query)
    try:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.core import Config

        config = Config(host=host, token=token)
        w = WorkspaceClient(config=config)
        response = w.serving_endpoints.query(
            name=DATABRICKS_FM_ENDPOINT,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.4,
        )
        if response and response.choices and len(response.choices) > 0:
            msg = response.choices[0].message
            out = (msg.content or "").strip() if msg else None
            if out:
                return out
    except Exception as e:
        logger.debug("Databricks SDK FM call failed: %s", e)

    # 2) Fallback: OpenAI-compatible REST (base_url = host/serving-endpoints)
    try:
        from openai import OpenAI

        base_url = f"{host}/serving-endpoints"
        client = OpenAI(api_key=token, base_url=base_url)
        response = client.chat.completions.create(
            model=DATABRICKS_FM_ENDPOINT,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.4,
        )
        if response and response.choices and len(response.choices) > 0:
            msg = response.choices[0].message
            out = (msg.content or "").strip() if msg else None
            if out:
                return out
    except Exception as e:
        logger.debug("OpenAI-style FM call failed: %s", e)

    return None


def generate_nba_and_email(contact: dict[str, Any]) -> tuple[str, str, str]:
    """
    Generate next best action and email draft for the contact using Databricks LLM.
    contact: dict with name, role_specialty, institution, priority_score, risk_level, intent_score,
             last_touch_days, preferred_channel, trx_volume_3m, nrx_volume_3m, rx_growth_3m_pct (optional).
    Returns (recommendation_text, email_subject, email_body).
    Falls back to MedTech-flavored static copy if LLM is not configured or call fails.
    """
    # Try LLM first
    nba_prompt = _build_nba_prompt(contact)
    nba_text = _call_databricks_chat([{"role": "user", "content": nba_prompt}], max_tokens=320)
    if nba_text:
        email_prompt = _build_email_prompt(contact)
        email_response = _call_databricks_chat([{"role": "user", "content": email_prompt}], max_tokens=1500)
        if email_response:
            subject, body = _parse_email_response(email_response)
            return (nba_text, subject, body)

    # Fallback: MedTech-specific static copy using contact context
    role = (contact.get("role_specialty") or "HCP").lower()
    institution = contact.get("institution") or "their institution"
    name = contact.get("name") or "there"
    if "surg" in role or "or " in role or "bariatric" in role or "gynec" in role:
        rec = (
            f"Prioritize re-engagement with a 15-minute virtual or phone touch within 72 hours. "
            f"Align to Ethicon surgical portfolio (stapling, wound closure, energy) and consider OTTAVA robotic program discussion for {institution}. "
            f"Offer clinical resources and adoption support (e.g. ECHELON, HARMONIC)."
        )
        subject = "Ethicon / OTTAVA – 15-min check-in this week?"
        body = (
            f"Hi {name},\n\n"
            f"I'm reaching out given your focus on surgery at {institution}. I'd like to reconnect and share how we're supporting practices like yours with our Ethicon surgical portfolio—including stapling, wound closure, and energy devices—and the OTTAVA robotic program.\n\n"
            f"We have clinical resources and adoption support that can help you get the most out of ECHELON and HARMONIC in your workflows. I'd value a brief 15-minute check-in to share what's new and hear how things are going on your side. Would you have time for a call this week or next?"
        )
    elif "vision" in role or "ophthal" in role or "refractive" in role or "eye" in role:
        rec = (
            f"Schedule a 15-minute touch within 72 hours. "
            f"Align to J&J Vision (IOL, refractive, contact lens) and consider TECNIS SYMFONY or ACUVUE adoption discussion for {institution}. "
            f"Share relevant clinical resources and fitting support."
        )
        subject = "J&J Vision – 15-min check-in this week?"
        body = (
            f"Hi {name},\n\n"
            f"Given your focus on vision care at {institution}, I wanted to reach out personally. We've been supporting practices with our J&J Vision portfolio—from IOLs and refractive options like TECNIS SYMFONY and ELITA to contact lens solutions such as ACUVUE OASYS and ACUVUE VITA.\n\n"
            f"I'd like to schedule a brief 15-minute check-in to share relevant clinical resources and fitting support that could benefit your patients. Would you have time for a call this week or next?"
        )
    elif "cardiac" in role or "cath" in role or "heart" in role or "interventional" in role:
        rec = (
            f"Rapid follow-up within 72 hours. "
            f"Align to Abiomed heart recovery and Impella utilization (Impella CP, 5.5) for {institution}. "
            f"Offer case discussion and adoption support."
        )
        subject = "Abiomed / Impella – 15-min check-in this week?"
        body = (
            f"Hi {name},\n\n"
            f"I'm reaching out given your focus on cardiac care at {institution}. Abiomed's heart recovery portfolio—including Impella CP and Impella 5.5—is helping teams support more patients, and I'd like to share how we can support your program.\n\n"
            f"I'd value a brief 15-minute check-in to discuss adoption support, case discussion, and resources that might be useful for your practice. Would you have time for a call this week or next?"
        )
    else:
        rec = (
            "Personalized re-engagement with rapid follow-up (15-minute virtual or phone touch within 72 hours). "
            f"Align to surgical/vision/cardiac portfolio interest (Ethicon, J&J Vision, OTTAVA, Abiomed) for {institution}."
        )
        subject = "J&J MedTech – 15-min check-in this week?"
        body = (
            f"Hi {name},\n\n"
            f"It's been a while since our last touch, and I wanted to reach out personally. I noticed your interest in our J&J MedTech portfolio—whether that's Ethicon surgical solutions, J&J Vision, OTTAVA robotic surgery, or Abiomed heart recovery—and I'd like to reconnect with you and your team at {institution}.\n\n"
            f"We have clinical resources and adoption support that can help you get the most from our products. I'd value a brief 15-minute check-in to share what's new and hear how things are going. Would you have time for a call this week or next?"
        )
    return (rec, subject, body)
