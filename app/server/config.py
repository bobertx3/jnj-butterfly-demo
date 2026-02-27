"""App config: Lakebase connection from env (PG*). In Databricks Apps, bind PGUSER/PGPASSWORD to secret scope."""

import os

# Lakebase Autoscale connection (batch_release_db)
# PGUSER and PGPASSWORD should be set from secret scope: lakebase-native-user (PGUSER), lakebase-native-password (PGPASSWORD)
PGHOST = os.environ.get("PGHOST", "ep-wandering-scene-d2440hao.database.us-east-1.cloud.databricks.com")
PGPORT = int(os.environ.get("PGPORT", "5432"))
PGDATABASE = os.environ.get("PGDATABASE", "batch_release_db")
PGUSER = os.environ.get("PGUSER", "")
PGPASSWORD = os.environ.get("PGPASSWORD", "")


def has_lakebase_credentials() -> bool:
    return bool(PGUSER and PGPASSWORD)
