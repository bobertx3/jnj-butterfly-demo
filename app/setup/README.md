# Next Best Action — Lakebase setup

Creates the `next_best_action` table in the Lakebase Autoscale database and seeds it with sample data aligned to the Butterfly demo (accounts, contacts, action types).

## Prerequisites

- Access to the Lakebase database: `batch_release_db` on `ep-wandering-scene-d2440hao.database.us-east-1.cloud.databricks.com`
- Credentials in a Databricks secret scope (or set env vars for local run):
  - `lakebase-native-user` → key `PGUSER`
  - `lakebase-native-password` → key `PGPASSWORD`

## Running the setup

### Option 1: Local profile (.env)

Copy `.env.example` to `.env` in this directory and set `PGUSER` and `PGPASSWORD` for a role that has CREATE (e.g. `databricks_all_writer_perms` from your local profile). Then run:

```bash
cd app/setup
python setup_lakebase.py
```

The script loads `app/setup/.env` or `app/.env` automatically.

### Option 2: Environment variables (local or CI)

```bash
export PGUSER="<your-lakebase-user>"
export PGPASSWORD="<your-lakebase-password>"
# Optional overrides:
# export PGHOST=ep-wandering-scene-d2440hao.database.us-east-1.cloud.databricks.com
# export PGPORT=5432
# export PGDATABASE=batch_release_db

cd app/setup
python setup_lakebase.py
```

### Option 2: Databricks notebook (secret scope)

In a notebook, set env from secrets then run the setup script logic, or:

```python
import os
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
# If your scope is e.g. "lakebase-creds":
os.environ["PGUSER"] = w.secrets.get_secret(scope="lakebase-creds", key="PGUSER")
os.environ["PGPASSWORD"] = w.secrets.get_secret(scope="lakebase-creds", key="PGPASSWORD")
# Then run setup_lakebase.main()
```

## What it does

1. Creates schema `app` if not exists.
2. Creates table `app.next_best_action` (id, account_id, contact_id, action_type, title, description, priority, status, due_date, created_at, updated_at).
3. Seeds the table with sample next-best-action rows (account/contact IDs and action types consistent with the Butterfly synthetic data).
