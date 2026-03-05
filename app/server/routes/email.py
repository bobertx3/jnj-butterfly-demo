"""Email sending route backed by Mailgun."""

from __future__ import annotations

import re
from typing import Optional

import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.config import MAILGUN_API_KEY, MAILGUN_API_URL, RECIPIENT, SENDER

router = APIRouter(prefix="/api/email", tags=["email"])

BG = "#f5f7fb"
INK = "#222"
RED = "#e24a4a"
BLUE = "#1e63c6"
DIV = "#e6edf6"
AGENT_NAME = "Next Best Action Agent"


class EmailSendRequest(BaseModel):
    recipient: Optional[str] = None
    subject: str = ""
    message: str = ""


def _as_list(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in re.split(r"[;,]", value) if v.strip()]


@router.post("/send")
async def send_email(body: EmailSendRequest) -> dict:
    missing = [
        k
        for k, v in {
            "MAILGUN_API_URL": MAILGUN_API_URL,
            "MAILGUN_API_KEY": MAILGUN_API_KEY,
            "SENDER": SENDER,
        }.items()
        if not v
    ]
    if missing:
        raise HTTPException(status_code=500, detail=f"Missing required env vars: {', '.join(missing)}")

    to_list = _as_list(body.recipient) or _as_list(RECIPIENT)
    if not to_list:
        raise HTTPException(status_code=400, detail="No recipient provided.")

    message = body.message or ""
    text = re.sub(r"<[^>]+>", "", message.replace("<br/>", "\n").replace("<br>", "\n"))
    html = f"""
    <html><body style='margin:0;padding:0;background:{BG};'>
    <table width='100%' style='background:{BG};'><tr><td align='center' style='padding:24px;'>
    <table width='640' style='max-width:640px;background:#fff;border-radius:14px;box-shadow:0 6px 18px rgba(0,0,0,.06);'>
    <tr><td style='padding:28px 26px;font-family:Segoe UI,Roboto,Arial,sans-serif;color:{INK};font-size:16px;'>
    <div style='font-size:34px;font-weight:800;color:{RED};'>Jackson &amp; Jackson</div>
    <div style='display:inline-block;background:{BLUE};color:#fff;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;margin:6px 0 14px 0;'>UPDATE</div>
    <hr style='border:none;border-top:1px solid {DIV};margin:10px 0 18px 0;'>
    <div>{message}</div>
    <hr style='border:none;border-top:1px solid {DIV};margin:24px 0 0 0;'>
    </td></tr></table></td></tr></table></body></html>
    """.strip()

    payload = {
        "from": f"{AGENT_NAME}<{SENDER}>",
        "to": to_list,
        "subject": body.subject or "Next Best Action follow-up",
        "text": text,
        "html": html,
        "h:Reply-To": SENDER,
    }

    auth = aiohttp.BasicAuth("api", MAILGUN_API_KEY)
    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.post(MAILGUN_API_URL, data=payload, timeout=20) as resp:
            resp_text = await resp.text()
            if resp.status < 200 or resp.status >= 300:
                raise HTTPException(status_code=502, detail=f"Mailgun error {resp.status}: {resp_text[:400]}")
            msg_id: str = "unknown"
            try:
                data = await resp.json()
                msg_id = data.get("id", "unknown")
            except Exception:
                pass
            return {"ok": True, "message": f"Email sent to {', '.join(to_list)}", "id": msg_id}
