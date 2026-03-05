"""
Genie Space proxy: natural language Q&A over sales/Butterfly data.
Uses Databricks Genie REST API (same pattern as jnj-eo-analytics-demo).
"""
import asyncio
import json
import logging
import os
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.databricks_auth import (
    get_auth_debug,
    get_oauth_token,
    get_workspace_host,
    has_databricks_auth,
)

router = APIRouter(prefix="/api/genie", tags=["genie"])

GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID", "").strip()
POLL_INTERVAL_SEC = 2
POLL_MAX_WAIT_SEC = 120


class GenieAskRequest(BaseModel):
    question: str
    conversation_id: Optional[str | int] = None  # API may send string or number
    debug: Optional[bool] = False


def _normalize_text_content(raw: Any) -> str:
    """Turn API text content (string or list of strings/blocks) into a single string."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, list):
        parts = []
        for item in raw:
            if isinstance(item, str):
                parts.append(item.strip())
            elif isinstance(item, dict) and "text" in item:
                parts.append(_normalize_text_content(item.get("text")))
            elif isinstance(item, dict) and "content" in item:
                parts.append(_normalize_text_content(item["content"]))
        return "\n".join(p for p in parts if p)
    return str(raw).strip() if raw else ""


def _extract_genie_answer(data: dict) -> dict[str, Any]:
    """Extract text_response, sql, columns, data from Genie message JSON. Never raises."""
    out: dict[str, Any] = {
        "text_response": "",
        "sql": None,
        "columns": None,
        "data": None,
        "row_count": None,
    }
    try:
        if not isinstance(data, dict):
            out["text_response"] = "No answer text available."
            return out
        attachments = data.get("attachments") or []
        if not isinstance(attachments, list):
            attachments = []
        text_response = ""
        sql = None
        columns = None
        data_rows = None

        for att in attachments:
            if not isinstance(att, dict):
                continue
            att_type = (att.get("type") or "").upper()
            # TEXT: content may be in att.text.content (string or array) or att.content
            if att_type == "TEXT":
                t = att.get("text")
                if isinstance(t, dict):
                    text_response = _normalize_text_content(t.get("content")) or text_response
                if not text_response:
                    text_response = _normalize_text_content(att.get("content")) or text_response
            elif att_type == "QUERY":
                query_info = att.get("query")
                if isinstance(query_info, dict):
                    sql = query_info.get("query") or query_info.get("sql") or sql
                    if isinstance(sql, list):
                        sql = "\n".join(str(s) for s in sql) if sql else ""
                    result_info = query_info.get("result") or {}
                    if isinstance(result_info, dict):
                        cols = result_info.get("columns") or []
                        rows = result_info.get("data") or []
                        if isinstance(cols, list) and isinstance(rows, list) and cols and rows:
                            columns = [c.get("name", f"col_{i}") if isinstance(c, dict) else f"col_{i}" for i, c in enumerate(cols)]
                            data_rows = [dict(zip(columns, row)) for row in rows if isinstance(row, (list, tuple))]

        if not text_response and isinstance(data.get("content"), str):
            text_response = data.get("content", "").strip()
        if not text_response:
            text_response = "No answer text available."

        out["text_response"] = text_response
        out["sql"] = sql
        out["columns"] = columns
        out["data"] = data_rows
        out["row_count"] = len(data_rows) if data_rows else None
    except Exception:
        out["text_response"] = out.get("text_response") or "No answer text available."
    return out


async def _poll_genie_message(
    session: aiohttp.ClientSession,
    host: str,
    headers: dict,
    conversation_id: str,
    message_id: str,
    include_raw: bool = False,
) -> dict[str, Any]:
    """Poll GET message until COMPLETED or FAILED. If include_raw, add raw_message to result."""
    url = f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conversation_id}/messages/{message_id}"
    for _ in range(POLL_MAX_WAIT_SEC // POLL_INTERVAL_SEC):
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                if resp.status == 404:
                    return {"error": "Genie space not found. Add the Genie space as an app resource (Configure > Resources > Genie space, key: genie-space)."}
                return {"error": f"Genie API error {resp.status}: {await resp.text()}"}
            data = await resp.json()
        # GET message may return payload at top level or under "message" key
        payload = data if not isinstance(data.get("message"), dict) else data["message"]
        status = (data.get("status") or payload.get("status") or "").upper()
        if status in ("COMPLETED", "COMPLETE"):
            extracted = _extract_genie_answer(payload)
            result = {"status": "COMPLETED", **extracted}
            if include_raw:
                result["_raw_message"] = data
            logger.info(
                "Genie message completed: text_len=%s has_sql=%s has_data=%s attachments_keys=%s",
                len(extracted.get("text_response") or ""),
                bool(extracted.get("sql")),
                bool(extracted.get("data")),
                [list(a.keys()) if isinstance(a, dict) else None for a in (data.get("attachments") or [])[:5]],
            )
            logger.debug("Genie raw message (debug): %s", json.dumps(data, default=str)[:2000])
            return result
        if status in ("FAILED", "CANCELLED"):
            return {"status": "FAILED", "error": data.get("error", "Unknown error")}
        await asyncio.sleep(POLL_INTERVAL_SEC)
    return {"status": "FAILED", "error": "Timed out waiting for Genie response."}


@router.get("/status")
async def genie_status() -> dict:
    """Return whether Genie is configured and space_id. Never raises."""
    try:
        auth_ok, auth_msg = get_auth_debug()
        configured = auth_ok and bool(GENIE_SPACE_ID)
        out = {
            "configured": configured,
            "space_id": GENIE_SPACE_ID or None,
        }
        if not configured:
            if not GENIE_SPACE_ID:
                out["message"] = (
                    "Add a Genie space as an app resource: Configure > Resources > Add resource > Genie space, set key to 'genie-space'."
                    if auth_ok
                    else auth_msg
                )
            else:
                out["message"] = auth_msg
        return out
    except Exception as e:
        return {
            "configured": False,
            "space_id": None,
            "message": str(e),
        }


@router.post("/ask")
async def genie_ask(body: GenieAskRequest) -> dict:
    """Ask the Genie space; uses REST API (start-conversation or messages) then poll for result.
    If body.debug=true, response includes _raw_message with the full Genie API message payload."""
    question = (body.question or "").strip()
    debug = body.debug or False
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    host = get_workspace_host()
    token = get_oauth_token()
    if not host or not token:
        _, msg = get_auth_debug()
        raise HTTPException(status_code=503, detail=msg or "Cannot authenticate to Databricks workspace.")
    if not GENIE_SPACE_ID:
        raise HTTPException(
            status_code=503,
            detail="GENIE_SPACE_ID not configured.",
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"content": question}

    if body.conversation_id and str(body.conversation_id).strip():
        conv_id = str(body.conversation_id).strip()
        url = f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conv_id}/messages"
    else:
        url = f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/start-conversation"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    if resp.status == 404:
                        raise HTTPException(
                            status_code=503,
                            detail="Genie space not found. Add the Genie space as an app resource: open your app > Configure > Resources > Add resource > Genie space, choose your space, set key to 'genie-space', then save and reopen the app.",
                        )
                    raise HTTPException(status_code=503, detail=f"Genie API error ({resp.status}): {err}")
                try:
                    result = await resp.json()
                except Exception as e:
                    raise HTTPException(status_code=503, detail=f"Invalid Genie response: {e}")

            if not isinstance(result, dict):
                raise HTTPException(status_code=503, detail="Genie API returned invalid response.")

            # API returns nested conversation.id and message.id (see Genie Conversation API docs)
            conv_obj = result.get("conversation") if isinstance(result.get("conversation"), dict) else {}
            msg_obj = result.get("message") if isinstance(result.get("message"), dict) else {}
            conversation_id = (
                conv_obj.get("id")
                or result.get("conversation_id")
                or body.conversation_id
            )
            message_id = msg_obj.get("id") or result.get("message_id") or result.get("id")
            if not conversation_id or not message_id:
                return {
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "status": "FAILED",
                    "text_response": "",
                    "error": "No conversation_id or message_id in response.",
                }

            poll_result = await _poll_genie_message(
                session, host, headers, conversation_id, message_id, include_raw=debug
            )
            if poll_result.get("error"):
                return {
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "status": "FAILED",
                    "text_response": "",
                    "error": poll_result["error"],
                }

            text_response = poll_result.get("text_response") or ""
            if not text_response and not poll_result.get("sql") and not poll_result.get("data"):
                text_response = (
                    "Query completed. No response content could be parsed from Genie. "
                    "Try asking with debug=true in the request body to see the raw payload."
                )

            out = {
                "conversation_id": conversation_id,
                "message_id": message_id,
                "status": poll_result.get("status", "COMPLETED"),
                "text_response": text_response,
                "sql": poll_result.get("sql"),
                "columns": poll_result.get("columns"),
                "data": poll_result.get("data"),
                "row_count": poll_result.get("row_count"),
            }
            if debug and "_raw_message" in poll_result:
                out["_raw_message"] = poll_result["_raw_message"]
                logger.info("Genie _raw_message keys: %s", list((poll_result.get("_raw_message") or {}).keys()))
            return out
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
