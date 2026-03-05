"""
Unit test: Genie space returns data for "what is total net sales".
Requires .env with DATABRICKS_HOST, DATABRICKS_TOKEN, GENIE_SPACE_ID.
Skips if not configured.
"""
import os
from pathlib import Path

import pytest

# Load .env before importing app (same order as app.py: repo root when cwd is app/, then app/.env)
_cwd = Path.cwd()
_repo_root_from_cwd = _cwd.parent if _cwd.name == "app" else _cwd
_repo_root_from_file = Path(__file__).resolve().parent.parent.parent
_app_dir = Path(__file__).resolve().parent.parent
for _p in (_repo_root_from_cwd / ".env", _repo_root_from_file / ".env", _app_dir / ".env"):
    if _p.exists():
        from dotenv import load_dotenv
        load_dotenv(_p)
        break

from fastapi.testclient import TestClient

# Run from app/ so app.py is importable as "app"
import app as _app_mod
client = TestClient(_app_mod.app)

GENIE_CONFIGURED = bool(
    os.environ.get("DATABRICKS_HOST", "").strip()
    and os.environ.get("DATABRICKS_TOKEN", "").strip()
    and os.environ.get("GENIE_SPACE_ID", "").strip()
)


@pytest.mark.skipif(not GENIE_CONFIGURED, reason="DATABRICKS_HOST, DATABRICKS_TOKEN, GENIE_SPACE_ID required in .env")
def test_genie_ask_returns_data_for_total_net_sales():
    """POST /api/genie/ask with 'what is total net sales' returns success and some content (text, sql, or data)."""
    response = client.post(
        "/api/genie/ask",
        json={"question": "what is total net sales"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("status") in ("COMPLETED", "COMPLETE"), data
    # At least one of: text response, SQL, or result data
    has_content = (
        (data.get("text_response") or "").strip() != ""
        or (data.get("sql") or "").strip() != ""
        or (data.get("data") is not None and len(data.get("data") or []) > 0)
    )
    assert has_content, f"Genie returned no content: {data}"
