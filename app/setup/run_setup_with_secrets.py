"""Load PGUSER/PGPASSWORD from Databricks secret scope jnj-batch-release-secrets, then run setup_lakebase."""
import base64
import os

from databricks.sdk import WorkspaceClient

SCOPE = "jnj-batch-release-secrets"


def _load_secret(w: WorkspaceClient, key: str) -> str:
    r = w.secrets.get_secret(scope=SCOPE, key=key)
    v = getattr(r, "value", None)
    if v is None:
        raise SystemExit(f"Missing {key} in scope {SCOPE}")
    if isinstance(v, bytes):
        return v.decode("utf-8")
    s = v if isinstance(v, str) else str(v)
    # Databricks often returns secret value as base64-encoded string
    try:
        decoded = base64.b64decode(s).decode("utf-8")
        if decoded.isprintable() or "\x00" not in decoded:
            return decoded
    except Exception:
        pass
    return s


if __name__ == "__main__":
    w = WorkspaceClient()
    os.environ["PGUSER"] = _load_secret(w, "PGUSER")
    os.environ["PGPASSWORD"] = _load_secret(w, "PGPASSWORD")
    from setup_lakebase import main
    import asyncio
    asyncio.run(main())
