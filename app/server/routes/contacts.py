"""Prioritized Contact Queue API: list contacts, get detail, get/update NBA, generate NBA (writes to Lakebase)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.config import has_databricks_llm_credentials
from server.db import db
from server.llm import generate_nba_and_email

router = APIRouter(prefix="/api/contacts", tags=["contacts"])
SCHEMA = "public"


class ContactOut(BaseModel):
    id: int
    contact_id: str
    name: str
    role_specialty: Optional[str]
    institution: Optional[str]
    priority_score: float
    intent_score: int
    risk_level: str
    preferred_channel: str
    last_touch_days: int
    last_interaction_channel: Optional[str] = None
    last_interaction_date: Optional[date] = None
    last_interaction_summary: Optional[str] = None
    last_products_discussed: Optional[str] = None
    next_follow_up_objective: Optional[str] = None
    trx_volume_3m: Optional[int]
    nrx_volume_3m: Optional[int]
    site_visits: Optional[int]
    webinar_signups: Optional[int]
    rx_growth_3m_pct: Optional[float]
    territory_id: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class NbaRecommendationOut(BaseModel):
    contact_id: str
    recommendation_text: Optional[str]
    email_draft_subject: Optional[str]
    email_draft_body: Optional[str]
    generated_at: Optional[datetime]


class NbaRecommendationUpdate(BaseModel):
    recommendation_text: Optional[str] = None
    email_draft_subject: Optional[str] = None
    email_draft_body: Optional[str] = None


def _row_to_contact(r: Any) -> ContactOut:
    return ContactOut(
        id=r["id"],
        contact_id=r["contact_id"],
        name=r["name"],
        role_specialty=r["role_specialty"],
        institution=r["institution"],
        priority_score=float(r["priority_score"]) if r["priority_score"] is not None else 0,
        intent_score=int(r["intent_score"]) if r["intent_score"] is not None else 0,
        risk_level=r["risk_level"] or "Medium",
        preferred_channel=r["preferred_channel"] or "Email",
        last_touch_days=int(r["last_touch_days"]) if r["last_touch_days"] is not None else 0,
        last_interaction_channel=r.get("last_interaction_channel"),
        last_interaction_date=r.get("last_interaction_date"),
        last_interaction_summary=r.get("last_interaction_summary"),
        last_products_discussed=r.get("last_products_discussed"),
        next_follow_up_objective=r.get("next_follow_up_objective"),
        trx_volume_3m=r["trx_volume_3m"],
        nrx_volume_3m=r["nrx_volume_3m"],
        site_visits=r["site_visits"],
        webinar_signups=r["webinar_signups"],
        rx_growth_3m_pct=float(r["rx_growth_3m_pct"]) if r["rx_growth_3m_pct"] is not None else None,
        territory_id=r["territory_id"],
        updated_at=r["updated_at"],
    )


@router.get("", response_model=List[ContactOut])
async def list_contacts(
    filter: Optional[str] = None,
    limit: int = 50,
) -> List[ContactOut]:
    """List contacts for the queue. filter: all | high_priority | at_risk | intent_spike | needs_outreach."""
    pool = await db.get_pool()
    if not pool:
        return _mock_contacts(limit)
    q = f"""
        SELECT id, contact_id, name, role_specialty, institution, priority_score, intent_score,
               risk_level, preferred_channel, last_touch_days, last_interaction_channel, last_interaction_date,
               last_interaction_summary, last_products_discussed, next_follow_up_objective, trx_volume_3m, nrx_volume_3m,
               site_visits, webinar_signups, rx_growth_3m_pct, territory_id, updated_at
        FROM "{SCHEMA}"."contact_queue"
    """
    params: List[Any] = []
    if filter == "high_priority":
        q += " WHERE priority_score >= 80"
    elif filter == "at_risk":
        q += " WHERE risk_level = 'High'"
    elif filter == "intent_spike":
        q += " WHERE intent_score >= 90"
    elif filter == "needs_outreach":
        q += " WHERE last_touch_days >= 30"
    q += " ORDER BY priority_score DESC, intent_score DESC, last_touch_days DESC NULLS LAST LIMIT $1"
    params.append(limit)
    async with pool.acquire() as conn:
        rows = await conn.fetch(q, *params)
    return [_row_to_contact(r) for r in rows]


@router.get("/llm-status")
async def get_llm_status() -> dict:
    """Return whether Databricks LLM is configured for NBA/email generation (for UI feedback)."""
    return {"llm_configured": has_databricks_llm_credentials()}


@router.get("/stats")
async def get_stats() -> dict:
    """Global KPIs for header: assigned_contacts, growth_opportunities, at_risk_accounts."""
    pool = await db.get_pool()
    if not pool:
        return {"assigned_contacts": 50, "growth_opportunities": 4, "at_risk_accounts": 15}
    async with pool.acquire() as conn:
        total = await conn.fetchval(f'SELECT COUNT(*) FROM "{SCHEMA}"."contact_queue"')
        at_risk = await conn.fetchval(
            f'SELECT COUNT(*) FROM "{SCHEMA}"."contact_queue" WHERE risk_level = $1', "High"
        )
        avg_priority = await conn.fetchval(
            f'SELECT ROUND(AVG(priority_score),0)::INT FROM "{SCHEMA}"."contact_queue" WHERE risk_level = $1',
            "High",
        )
    return {
        "assigned_contacts": total or 0,
        "growth_opportunities": 4,
        "at_risk_accounts": at_risk or 0,
        "at_risk_avg_priority": avg_priority or 0,
    }


@router.get("/{contact_id}", response_model=ContactOut)
async def get_contact(contact_id: str) -> ContactOut:
    """Get one contact by contact_id."""
    pool = await db.get_pool()
    if not pool:
        for c in _mock_contacts(5):
            if c.contact_id == contact_id:
                return c
        raise HTTPException(status_code=404, detail="Contact not found")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            SELECT id, contact_id, name, role_specialty, institution, priority_score, intent_score,
                   risk_level, preferred_channel, last_touch_days, last_interaction_channel, last_interaction_date,
                   last_interaction_summary, last_products_discussed, next_follow_up_objective, trx_volume_3m, nrx_volume_3m,
                   site_visits, webinar_signups, rx_growth_3m_pct, territory_id, updated_at
            FROM "{SCHEMA}"."contact_queue" WHERE contact_id = $1
            """,
            contact_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Contact not found")
    return _row_to_contact(row)


@router.get("/{contact_id}/nba", response_model=NbaRecommendationOut)
async def get_nba(contact_id: str) -> NbaRecommendationOut:
    """Get NBA recommendation for a contact."""
    pool = await db.get_pool()
    if not pool:
        # Local/mock mode should mirror empty pre-generate state.
        return NbaRecommendationOut(contact_id=contact_id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            SELECT contact_id, recommendation_text, email_draft_subject, email_draft_body, generated_at
            FROM "{SCHEMA}"."nba_recommendation" WHERE contact_id = $1
            """,
            contact_id,
        )
    if not row:
        return NbaRecommendationOut(contact_id=contact_id)
    return NbaRecommendationOut(
        contact_id=row["contact_id"],
        recommendation_text=row["recommendation_text"],
        email_draft_subject=row["email_draft_subject"],
        email_draft_body=row["email_draft_body"],
        generated_at=row["generated_at"],
    )


@router.post("/{contact_id}/nba/generate", response_model=NbaRecommendationOut)
async def generate_nba(contact_id: str) -> NbaRecommendationOut:
    """Generate or refresh NBA (and email draft) for contact via Databricks LLM; writes to Lakebase. MedTech-aligned copy."""
    pool = await db.get_pool()
    contact_ctx: dict[str, Any] = {
        "contact_id": contact_id,
        "name": "",
        "role_specialty": None,
        "institution": None,
        "priority_score": 0,
        "risk_level": "Medium",
        "intent_score": 0,
        "last_touch_days": 0,
        "preferred_channel": "Email",
        "trx_volume_3m": None,
        "nrx_volume_3m": None,
        "rx_growth_3m_pct": None,
        "last_interaction_channel": None,
        "last_interaction_date": None,
        "last_interaction_summary": None,
        "last_products_discussed": None,
        "next_follow_up_objective": None,
    }
    if pool:
        async with pool.acquire() as conn:
            col_rows = await conn.fetch(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = $1 AND table_name = 'contact_queue'
                """,
                SCHEMA,
            )
            contact_cols = {r["column_name"] for r in col_rows}
            extra_select = [
                "last_interaction_channel"
                if "last_interaction_channel" in contact_cols
                else "NULL::text AS last_interaction_channel",
                "last_interaction_date"
                if "last_interaction_date" in contact_cols
                else "NULL::date AS last_interaction_date",
                "last_interaction_summary"
                if "last_interaction_summary" in contact_cols
                else "NULL::text AS last_interaction_summary",
                "last_products_discussed"
                if "last_products_discussed" in contact_cols
                else "NULL::text AS last_products_discussed",
                "next_follow_up_objective"
                if "next_follow_up_objective" in contact_cols
                else "NULL::text AS next_follow_up_objective",
            ]
            row = await conn.fetchrow(
                f"""
                SELECT contact_id, name, role_specialty, institution, priority_score, intent_score,
                       risk_level, preferred_channel, last_touch_days, trx_volume_3m, nrx_volume_3m, rx_growth_3m_pct,
                       {", ".join(extra_select)}
                FROM "{SCHEMA}"."contact_queue" WHERE contact_id = $1
                """,
                contact_id,
            )
            if row:
                contact_ctx = {
                    "contact_id": row["contact_id"],
                    "name": row["name"] or "",
                    "role_specialty": row["role_specialty"],
                    "institution": row["institution"],
                    "priority_score": float(row["priority_score"]) if row["priority_score"] is not None else 0,
                    "risk_level": row["risk_level"] or "Medium",
                    "intent_score": int(row["intent_score"]) if row["intent_score"] is not None else 0,
                    "last_touch_days": int(row["last_touch_days"]) if row["last_touch_days"] is not None else 0,
                    "preferred_channel": row["preferred_channel"] or "Email",
                    "trx_volume_3m": row["trx_volume_3m"],
                    "nrx_volume_3m": row["nrx_volume_3m"],
                    "rx_growth_3m_pct": float(row["rx_growth_3m_pct"]) if row["rx_growth_3m_pct"] is not None else None,
                    "last_interaction_channel": row["last_interaction_channel"],
                    "last_interaction_date": row["last_interaction_date"],
                    "last_interaction_summary": row["last_interaction_summary"],
                    "last_products_discussed": row["last_products_discussed"],
                    "next_follow_up_objective": row["next_follow_up_objective"],
                }
    rec, subject, body = generate_nba_and_email(contact_ctx)
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO "{SCHEMA}"."nba_recommendation"
                (contact_id, recommendation_text, email_draft_subject, email_draft_body, generated_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                ON CONFLICT (contact_id) DO UPDATE SET
                recommendation_text=EXCLUDED.recommendation_text,
                email_draft_subject=EXCLUDED.email_draft_subject,
                email_draft_body=EXCLUDED.email_draft_body,
                generated_at=NOW(), updated_at=NOW()
                """,
                contact_id, rec, subject, body,
            )
            row = await conn.fetchrow(
                f'SELECT contact_id, recommendation_text, email_draft_subject, email_draft_body, generated_at FROM "{SCHEMA}"."nba_recommendation" WHERE contact_id = $1',
                contact_id,
            )
            if row:
                return NbaRecommendationOut(
                    contact_id=row["contact_id"],
                    recommendation_text=row["recommendation_text"],
                    email_draft_subject=row["email_draft_subject"],
                    email_draft_body=row["email_draft_body"],
                    generated_at=row["generated_at"],
                )
    return NbaRecommendationOut(
        contact_id=contact_id,
        recommendation_text=rec,
        email_draft_subject=subject,
        email_draft_body=body,
        generated_at=datetime.utcnow(),
    )


@router.patch("/{contact_id}")
async def update_contact_last_touch(contact_id: str, last_touch_days: int = 0) -> dict:
    """Update contact (e.g. set last_touch_days to 0 after logging an outreach); writes to Lakebase."""
    pool = await db.get_pool()
    if not pool:
        return {"ok": True}
    async with pool.acquire() as conn:
        await conn.execute(
            f'UPDATE "{SCHEMA}"."contact_queue" SET last_touch_days = $1, updated_at = NOW() WHERE contact_id = $2',
            last_touch_days,
            contact_id,
        )
    return {"ok": True}


def _mock_contacts(limit: int) -> List[ContactOut]:
    from datetime import timezone
    base = datetime.now(timezone.utc)
    # MedTech-aligned: surgical, vision, cardiac roles and institutions (Ethicon, J&J Vision, OTTAVA, Abiomed)
    roles = [
        "General Surgeon", "Cardiovascular Surgeon", "Ophthalmologist", "Interventional Cardiologist",
        "Surgical Lead", "Cath Lab Director",
    ]
    institutions = [
        "Evergreen Surgical Center", "Metro Heart & Vascular Institute", "Northview Ophthalmology Associates",
        "Central Surgical Institute", "Valley Regional Hospital", "Ridgeview Eye Institute",
    ]
    return [
        ContactOut(
            id=i,
            contact_id=f"HCP-{i:05d}",
            name=["Kai Price", "Reese Rivera", "Jordan Morris", "Hayden Diaz", "Casey Diaz"][i % 5],
            role_specialty=roles[i % len(roles)],
            institution=institutions[i % len(institutions)],
            priority_score=86 - i * 2,
            intent_score=100,
            risk_level="High" if i % 3 == 0 else "Medium",
            preferred_channel="Email",
            last_touch_days=39,
            trx_volume_3m=35,
            nrx_volume_3m=3,
            site_visits=7,
            webinar_signups=3,
            rx_growth_3m_pct=-36.4,
            territory_id="TERRITORY-001",
            updated_at=base,
        )
        for i in range(1, min(limit + 1, 6))
    ]
