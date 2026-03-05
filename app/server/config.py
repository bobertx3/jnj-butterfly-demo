"""App config: Lakebase connection from env (PG*). In Databricks Apps, bind PGUSER/PGPASSWORD to secret scope."""

import os

# Lakebase Autoscale connection (batch_release_db)
# PGUSER and PGPASSWORD should be set from secret scope: lakebase-native-user (PGUSER), lakebase-native-password (PGPASSWORD)
PGHOST = os.environ.get("PGHOST", "ep-wandering-scene-d2440hao.database.us-east-1.cloud.databricks.com")
PGPORT = int(os.environ.get("PGPORT", "5432"))
PGDATABASE = os.environ.get("PGDATABASE", "batch_release_db")
PGUSER = os.environ.get("PGUSER", "")
PGPASSWORD = os.environ.get("PGPASSWORD", "")

# Databricks workspace and Foundation Model API (for NBA + email generation).
# In Databricks Apps, DATABRICKS_HOST and DATABRICKS_CLIENT_ID/SECRET are auto-injected; or set DATABRICKS_TOKEN.
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")
DATABRICKS_CLIENT_ID = os.environ.get("DATABRICKS_CLIENT_ID", "")
DATABRICKS_CLIENT_SECRET = os.environ.get("DATABRICKS_CLIENT_SECRET", "")
DATABRICKS_FM_ENDPOINT = os.environ.get("DATABRICKS_FM_ENDPOINT", "databricks-claude-sonnet-4-6")

# Genie space for Sales data Q&A (natural language SQL over Butterfly/sales data).
# Set GENIE_SPACE_ID to your Genie space ID, or leave unset to try lookup by name "Butterfly Analytics".
GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID", "").strip()
GENIE_SPACE_DISPLAY_NAME = os.environ.get("GENIE_SPACE_DISPLAY_NAME", "Butterfly Analytics")


def has_lakebase_credentials() -> bool:
    return bool(PGUSER and PGPASSWORD)


def has_databricks_llm_credentials() -> bool:
    """True if we can call Foundation Model API: host + (token or OAuth)."""
    if not DATABRICKS_HOST:
        return False
    if DATABRICKS_TOKEN:
        return True
    return bool(DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET)


def has_genie_credentials() -> bool:
    """True if we can call Genie: host + (token or OAuth client_id/secret)."""
    if not DATABRICKS_HOST:
        return False
    if DATABRICKS_TOKEN:
        return True
    return bool(DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET)
