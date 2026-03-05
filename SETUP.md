# Databricks Butterfly Medallion + Data Quality

This project implements:

- Synthetic source-data generation into `bx4.butterfly.raw_landing` (CSV files in a Unity Catalog volume)
- SQL Lakeflow medallion pipeline (`bronze` -> `silver` -> `gold`)
- Customer 360 dashboard definition
- API-driven Databricks Data Quality monitor setup
- Data quality dashboard definition

## Project Layout

- `databricks.yml` - Databricks Asset Bundle root config
- `resources/butterfly_etl.pipeline.yml` - Lakeflow pipeline resource
- `resources/butterfly_dashboards.yml` - dashboard resources
- `resources/butterfly_jobs.yml` - job: pipeline → DQ monitors → dashboard refresh
- `resources/next_best_action_app.app.yml` - Next Best Action Databricks App (Lakebase backend)
- `app/` - Next Best Action app (FastAPI + React, J&J theme)
- `app/setup/` - Lakebase table creation and seed script for `app.next_best_action`
- `setup/` - schema/volume provisioning and synthetic data generator
- `src/butterfly_etl/transformations/` - medallion SQL transformations
- `monitoring/` - DQ monitor API script + DQ reporting SQL views
- `dashboards/` - dashboard JSON definitions + query validation SQL

## 1) Prerequisites

- Databricks CLI authenticated (`databricks auth login` or configured profile)
- Unity Catalog permissions to create/refresh pipeline tables in `bx4.butterfly`
- Permission to create Data Quality monitors and dashboards
- A SQL warehouse ID (set `var.warehouse_id` in `databricks.yml` or target overrides)

## 2) Generate Synthetic CSV Inputs

### 2.1 Create catalog/schema/volume

Run `setup/01_create_infrastructure.sql` in Databricks SQL:

```sql
CREATE CATALOG IF NOT EXISTS bx4;
CREATE SCHEMA IF NOT EXISTS bx4.butterfly;
CREATE VOLUME IF NOT EXISTS bx4.butterfly.raw_landing;
```

### 2.2 Generate data files

Run `setup/generate_synthetic_data.py` on Databricks (cluster or serverless notebook context).

Output folders are written to:

- `/Volumes/bx4/butterfly/raw_landing/account`
- `/Volumes/bx4/butterfly/raw_landing/contact`
- `/Volumes/bx4/butterfly/raw_landing/consent`
- `/Volumes/bx4/butterfly/raw_landing/product`
- `/Volumes/bx4/butterfly/raw_landing/alignment`
- `/Volumes/bx4/butterfly/raw_landing/employee`
- `/Volumes/bx4/butterfly/raw_landing/transactions`
- `/Volumes/bx4/butterfly/raw_landing/activities`
- `/Volumes/bx4/butterfly/raw_landing/opportunities`
- `/Volumes/bx4/butterfly/raw_landing/cases`

## 3) Deploy + Run Lakeflow Pipeline

```bash
databricks bundle validate
databricks bundle deploy
databricks bundle run butterfly_etl
```

The pipeline creates bronze/silver/gold tables in `bx4.butterfly`.

## 4) Data Quality Monitoring (API)

Run monitor creation and refresh:

```bash
python monitoring/create_data_quality_monitors.py
```

This script:

- Creates or reuses monitors for key silver/gold tables
- Triggers monitor refreshes
- Persists monitor metadata into `bx4.butterfly.dq_monitor_registry` (when run in Spark context)

Reporting views (`dq_rule_results`, `dq_monitor_assets`, `dq_summary`) are created automatically by the DQ script when the job runs, so the Data Quality dashboard has data after each run. To create or recreate them manually (e.g. in Databricks SQL), run `monitoring/dq_reporting.sql`. The script creates:

- `bx4.butterfly.dq_rule_results`
- `bx4.butterfly.dq_monitor_assets`
- `bx4.butterfly.dq_summary`

## 4b) Job: Pipeline + DQ + Dashboard Refresh

A single job runs the pipeline, then the data quality script, then refreshes both dashboards:

- **Task 1** `run_pipeline`: runs the Lakeflow pipeline (`butterfly_etl`).
- **Task 2** `run_dq_monitors`: runs `monitoring/create_data_quality_monitors.py` (create/refresh DQ monitors).
- **Task 3** `refresh_customer360_dashboard`: refreshes the Customer 360 dashboard.
- **Task 4** `refresh_dq_dashboard`: refreshes the Data Quality dashboard.

Ensure `variables.warehouse_id` is set (e.g. in `databricks.yml` or your target) so dashboard refresh tasks have a SQL warehouse. Deploy and run:

```bash
databricks bundle deploy
databricks bundle run butterfly_pipeline_and_dq
```

You can also schedule this job or trigger it from the Jobs UI.

## 4c) Next Best Action App (Lakebase Autoscale)

A minimal Databricks App lists and updates **next best actions** stored in Lakebase Autoscale:

- **Backend**: FastAPI + asyncpg → `batch_release_db` on `ep-wandering-scene-d2440hao.database.us-east-1.cloud.databricks.com`
- **Frontend**: React + Vite + Tailwind, Johnson & Johnson theme
- **Table**: `app.next_best_action` (created and seeded by `app/setup/setup_lakebase.py`)

**One-time setup**: Configure `PGUSER` and `PGPASSWORD` from your secret scope (e.g. `lakebase-native-user` / `lakebase-native-password` with keys `PGUSER` / `PGPASSWORD`). Run the setup script to create the table and seed data:

```bash
cd app/setup && export PGUSER=... PGPASSWORD=... && python setup_lakebase.py
```

**Deploy and run**:

```bash
databricks bundle deploy
databricks bundle run next_best_action_app
```

In **Apps** > **next-best-action-prod** (or your target) > **Edit**, add environment variables `PGUSER` and `PGPASSWORD` from your secret scope, then redeploy. See `app/README.md` for local run and build.

## 5) Dashboards

Definitions:

- `dashboards/customer360_dashboard.json`
- `dashboards/data_quality_dashboard.json`

Bundle resource file:

- `resources/butterfly_dashboards.yml`

Deploy with bundle:

```bash
databricks bundle deploy
```

## 6) Dataset Query Validation (Before Publishing Dashboards)

Run all dataset queries in:

- `dashboards/validate_queries.sql`

Validation can be done via Databricks SQL editor or MCP `execute_sql_multi`.

### Current validation status in this session

Validation was executed against a Databricks SQL warehouse, and queries failed with `TABLE_OR_VIEW_NOT_FOUND` for:

- `bx4.butterfly.gold_customer_360`
- `bx4.butterfly.gold_region_performance`
- `bx4.butterfly.gold_activity_trend_30d`
- `bx4.butterfly.dq_summary`
- `bx4.butterfly.dq_rule_results`
- `bx4.butterfly.dq_monitor_assets`

This is expected until steps 2-4 are run in order.

## 7) Execution Order Summary

1. Provision UC objects (`setup/01_create_infrastructure.sql`)
2. Generate synthetic CSV source data (`setup/generate_synthetic_data.py`)
3. Deploy and run pipeline (`databricks bundle deploy` + `databricks bundle run butterfly_etl`)
4. Create/refresh DQ monitors (`monitoring/create_data_quality_monitors.py`), or run the job (4b) to do pipeline + DQ + dashboard refresh in one go
5. Create DQ reporting views (`monitoring/dq_reporting.sql`)
6. Validate dashboard SQL (`dashboards/validate_queries.sql`)
7. Deploy dashboards (`databricks bundle deploy`)
