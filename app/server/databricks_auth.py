"""
Databricks workspace auth for API calls.
When running as a Databricks App, DATABRICKS_HOST and OAuth (or DATABRICKS_TOKEN) are set.
"""
import os
from typing import Optional, Tuple


def get_workspace_host() -> str:
    """Workspace URL with https:// (from env when DATABRICKS_APP_NAME is set)."""
    host = (os.environ.get("DATABRICKS_HOST") or "").strip().rstrip("/")
    if host and not host.startswith("http"):
        host = f"https://{host}"
    return host


def get_oauth_token() -> Optional[str]:
    """
    Bearer token for REST API calls.
    1. Use DATABRICKS_TOKEN from env if set (e.g. app secret).
    2. Else use WorkspaceClient() so SDK resolves env (OAuth in Apps).
    """
    token = (os.environ.get("DATABRICKS_TOKEN") or "").strip()
    if token:
        return token
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        if getattr(w.config, "token", None):
            return w.config.token
        auth = w.config.authenticate()
        if auth and "Authorization" in auth:
            return auth["Authorization"].replace("Bearer ", "")
    except Exception:
        pass
    return None


def has_databricks_auth() -> bool:
    """True if we can call Databricks APIs (host + token)."""
    return bool(get_workspace_host() and get_oauth_token())


def get_auth_debug() -> Tuple[bool, str]:
    """Return (ok, message) for debugging auth without raising."""
    host = get_workspace_host()
    token = get_oauth_token()
    if not host:
        return False, "DATABRICKS_HOST not set"
    if not token:
        return False, "No token (set DATABRICKS_TOKEN or use OAuth)"
    return True, "ok"
