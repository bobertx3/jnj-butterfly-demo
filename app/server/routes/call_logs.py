"""Call log analysis over Databricks Vector Search index."""

from __future__ import annotations

from typing import Any

import aiohttp
from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.config import CALL_LOG_SOURCE_TABLE, CALL_LOG_VECTOR_INDEX_NAME, VECTOR_SEARCH_ENDPOINT_NAME
from server.databricks_auth import get_auth_debug, get_oauth_token, get_workspace_host
from server.llm import _call_databricks_chat

router = APIRouter(prefix="/api/call-logs", tags=["call_logs"])


class CallLogAskRequest(BaseModel):
    question: str


def _extract_chunks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = payload.get("result") if isinstance(payload, dict) else None
    data_array = result.get("data_array") if isinstance(result, dict) else None
    if not isinstance(data_array, list):
        return []

    cols = []
    manifest = payload.get("manifest")
    if isinstance(manifest, dict) and isinstance(manifest.get("columns"), list):
        cols = [c.get("name") if isinstance(c, dict) else str(c) for c in manifest["columns"]]

    out: list[dict[str, Any]] = []
    for row in data_array:
        if isinstance(row, dict):
            out.append(row)
            continue
        if isinstance(row, list) and cols:
            out.append({cols[i]: row[i] if i < len(row) else None for i in range(len(cols))})
    return out


@router.get("/status")
async def call_log_status() -> dict[str, Any]:
    auth_ok, auth_msg = get_auth_debug()
    configured = auth_ok and bool(CALL_LOG_VECTOR_INDEX_NAME)
    return {
        "configured": configured,
        "vector_endpoint": VECTOR_SEARCH_ENDPOINT_NAME or None,
        "vector_index": CALL_LOG_VECTOR_INDEX_NAME or None,
        "source_table": CALL_LOG_SOURCE_TABLE or None,
        "message": None if configured else auth_msg,
    }


@router.post("/chat")
async def ask_call_logs(body: CallLogAskRequest) -> dict[str, Any]:
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    host = get_workspace_host()
    token = get_oauth_token()
    if not host or not token:
        _, msg = get_auth_debug()
        raise HTTPException(status_code=503, detail=msg or "Cannot authenticate to Databricks workspace.")

    index_name = CALL_LOG_VECTOR_INDEX_NAME
    if not index_name:
        raise HTTPException(status_code=503, detail="CALL_LOG_VECTOR_INDEX_NAME is not configured.")

    # Return a friendly status when index is still provisioning.
    try:
        idx = WorkspaceClient().vector_search_indexes.get_index(index_name)
        if idx.status and not idx.status.ready:
            status_msg = idx.status.message or "Vector index is provisioning."
            return {
                "answer": f"Call log index is still provisioning. {status_msg}",
                "citations": [],
                "retrieved_chunks": [],
            }
    except Exception:
        # Continue to API query path for explicit error messaging.
        pass

    query_payload = {
        "query_text": question,
        "num_results": 5,
        "columns": ["chunk_id", "document_name", "source_path", "chunk_index", "chunk_text"],
    }
    url = f"{host}/api/2.0/vector-search/indexes/{index_name}/query"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=query_payload, headers=headers) as resp:
            raw = await resp.text()
            if resp.status != 200:
                raise HTTPException(status_code=503, detail=f"Vector index query failed ({resp.status}): {raw[:500]}")
            data = await resp.json()

    chunks = _extract_chunks(data)
    if not chunks:
        return {
            "answer": "I could not find relevant call-log chunks yet. Verify the call-log PDF was ingested and the vector index is synced.",
            "citations": [],
            "retrieved_chunks": [],
        }

    context_lines = []
    citations = []
    for c in chunks:
        chunk_id = c.get("chunk_id") or "unknown_chunk"
        doc_name = c.get("document_name") or "unknown_document"
        chunk_text = str(c.get("chunk_text") or "").strip()
        if not chunk_text:
            continue
        context_lines.append(f"[{chunk_id}] ({doc_name}) {chunk_text}")
        citations.append({"chunk_id": chunk_id, "document_name": doc_name})

    prompt = (
        "You are a sales-assistant analyst for Jackson and Jackson.\n"
        "Answer the question using only the retrieved call transcript context.\n"
        "If context is insufficient, say what is missing.\n"
        "Keep answer concise and actionable for a sales rep.\n\n"
        f"Question:\n{question}\n\n"
        "Retrieved context:\n"
        + "\n\n".join(context_lines[:5])
    )

    llm_answer = _call_databricks_chat([{"role": "user", "content": prompt}], max_tokens=600)
    answer = llm_answer or "I found relevant transcript chunks, but the LLM response was unavailable."
    return {"answer": answer, "citations": citations, "retrieved_chunks": chunks[:5]}
