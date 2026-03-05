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

1. Creates table `public.next_best_action` (and seeds it with `setup_lakebase.py`).

## Prioritized Contact Queue (contact_queue + nba_recommendation)

The UI uses two additional tables. **Run the DDL once** (requires CREATE on `public`), then **seed** with your usual Lakebase user.

### 1. Create tables (run in batch_release_db as an admin or role with CREATE)

```bash
# From project root, apply the SQL (e.g. via psql or Databricks SQL)
psql "<connection-string>" -f app/setup/lakebase_contact_queue_ddl.sql
```

Or paste the contents of `app/setup/lakebase_contact_queue_ddl.sql` into Databricks SQL and run against `batch_release_db`.

### 2. Seed contact queue and NBA recommendations

Uses the same `.env` as above. Inserts 50 contacts and 50 NBA recommendation rows.

```bash
cd app/setup
python seed_contact_queue.py
```
