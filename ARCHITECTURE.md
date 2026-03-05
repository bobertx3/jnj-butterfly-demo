# Architecture

## System Overview

**jnj-butterfly-demo** is a Databricks-centric project with (1) a Lakeflow medallion pipeline and Data Quality stack that ingests synthetic CSV data into Unity Catalog and produces bronze/silver/gold tables plus DQ monitors and dashboards, and (2) a **Next Best Action** web app (FastAPI + React) that lists/updates actions and contacts from Lakebase Autoscale, generates NBA/email copy via the Databricks Foundation Model API, and runs natural-language Q&A over sales data via a Genie space.

---

## Request Flow

```
Browser (React SPA)
    │
    ▼ fetch /api/*  (Vite proxy → :8000 in dev; same-origin in prod)
    │
FastAPI (app/app.py)
    ├── /api/actions/*   → server/routes/actions.py   → Lakebase (asyncpg) or mock
    ├── /api/contacts/*  → server/routes/contacts.py → Lakebase + optional LLM (server/llm.py)
    └── /api/genie/*     → server/routes/genie.py     → Databricks Genie REST API (auth via server/databricks_auth.py)
    │
    ▼ (when Lakebase configured)
Lakebase Autoscale (PostgreSQL) — batch_release_db
    │
    ▼ (when Genie/LLM configured)
Databricks workspace — Genie Conversation API, Foundation Model API
```

---

## Component Details

### Next Best Action App (app/)

| Aspect | Detail |
|--------|--------|
| **Framework** | **FastAPI** (Python), **React** + **Vite** + **Tailwind** (frontend) |
| **Entry** | `app/app.py` — mounts routers, CORS, static SPA from `frontend/dist` |
| **Config** | `server/config.py` — all settings from `os.environ` (see table below) |

**Config / env (app)**

| Field | Default | Purpose |
|-------|---------|---------|
| `PGHOST` | `ep-wandering-scene-d2440hao.database.us-east-1.cloud.databricks.com` | Lakebase instance |
| `PGPORT` | `5432` | Lakebase port |
| `PGDATABASE` | `batch_release_db` | Lakebase database |
| `PGUSER` | (empty) | Lakebase user (required for real data) |
| `PGPASSWORD` | (empty) | Lakebase password |
| `DATABRICKS_HOST` | (empty) | Workspace URL for LLM and Genie |
| `DATABRICKS_TOKEN` | (empty) | Bearer token (or OAuth in Apps) |
| `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET` | (empty) | OAuth when running as Databricks App |
| `DATABRICKS_FM_ENDPOINT` | `databricks-claude-sonnet-4-6` | Foundation Model for NBA/email |
| `GENIE_SPACE_ID` | (empty) | Genie space for Sales data Q&A tab |
| `GENIE_SPACE_DISPLAY_NAME` | `Butterfly Analytics` | Display / lookup name |

**Key files**

- `app.py` — FastAPI app, routers, static mount, shutdown close of DB pool.
- `server/db.py` — asyncpg pool; `get_pool()` returns `None` when `PGUSER`/`PGPASSWORD` missing (mock mode).
- `server/config.py` — env-driven config and `has_*_credentials()` helpers.
- `server/databricks_auth.py` — `get_workspace_host()`, `get_oauth_token()` (env or **databricks-sdk** `WorkspaceClient`).
- `server/routes/actions.py` — list/patch actions; uses Lakebase or `_mock_actions()`.
- `server/routes/contacts.py` — contacts list/detail, NBA get/generate/patch; calls `server/llm.py` for generation.
- `server/routes/genie.py` — `/status`, `/ask`; calls Genie start-conversation / messages and polls get-message.
- `server/llm.py` — Foundation Model API client for NBA + email draft.
- `frontend/src/App.tsx` — single-page UI: contact queue, NBA, Genie Q&A tab; `API = "/api"`.

**Main flow (Genie ask)**

```text
POST /api/genie/ask → get_workspace_host() + get_oauth_token()
  → POST .../start-conversation or .../conversations/{id}/messages
  → poll GET .../messages/{message_id} until COMPLETED
  → _extract_genie_answer(payload) → { text_response, sql, columns, data }
  → return JSON to frontend
```

### Lakeflow Pipeline & DQ

| Aspect | Detail |
|--------|--------|
| **Defined in** | `resources/butterfly_etl.pipeline.yml` — catalog/schema/raw_volume from bundle vars |
| **Stages** | Bronze (foundational) → Silver (conformed) → Gold (customer360) SQL in `src/butterfly_etl/transformations/` |
| **DQ** | `monitoring/create_data_quality_monitors.py` — creates/refreshes monitors; `monitoring/dq_reporting.sql` for views |
| **Job** | `resources/butterfly_jobs.yml` — pipeline → DQ → dashboard refresh (requires `var.warehouse_id`) |

### Dashboards

- `resources/butterfly_dashboards.yml` — Customer 360 and Data Quality dashboards; dataset catalog/schema/warehouse from bundle variables.
- JSON under `dashboards/`; validation SQL in `dashboards/validate_queries.sql`.

---

## Infrastructure / External Services

- **Lakebase Autoscale (PostgreSQL)**  
  - Host: `ep-wandering-scene-d2440hao.database.us-east-1.cloud.databricks.com`  
  - DB: `batch_release_db`  
  - App tables: `public.next_best_action`, contact-queue tables (see `app/setup/`).  
  - Access: `PGUSER` / `PGPASSWORD` (or Secret resources in Databricks App).

- **Databricks workspace**  
  - **Genie**: Conversation API (`/api/2.0/genie/spaces/{space_id}/start-conversation`, `.../messages`, GET message).  
  - **Foundation Model API**: NBA and email generation (model from `DATABRICKS_FM_ENDPOINT`).  
  - Auth: `DATABRICKS_HOST` + `DATABRICKS_TOKEN`, or OAuth (`DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET`) when run as Databricks App.

- **Unity Catalog**  
  - Catalog/schema: `bx4.butterfly` (bundle vars `var.catalog`, `var.schema`).  
  - Volume: `bx4.butterfly.raw_landing` for synthetic CSV landing.  
  - Pipeline writes bronze/silver/gold tables; DQ views in same schema.

---

## Data Pipeline

```text
CSV in UC volume (raw_landing/*)
    │
    ▼ Lakeflow pipeline (butterfly_etl)
Bronze (bronze_foundational.sql)
    ▼
Silver (silver_conformed.sql)
    ▼
Gold (gold_customer360.sql)
    ▼
DQ monitors (create_data_quality_monitors.py) → dq_* views
    ▼
Dashboards (Customer 360, Data Quality) — refresh via job
```

---

## Deployment

### Next Best Action App (Databricks App)

- **Bundle**: `resources/next_best_action_app.app.yml` — app resource, Genie space attachment; app config in `app/app.yaml` (env from Secret/genie-space).
- **Build frontend**: `cd app/frontend && npm ci && npm run build` → `app/frontend/dist`.
- **Deploy**: from repo root, `databricks bundle deploy -t prod` (or `-t dev`).
- **Run**: `databricks bundle run next_best_action_app -t prod`.
- **Config**: In Apps UI, add Secret resources `lakebase-native-user`, `lakebase-native-password`; Genie space key `genie-space` per `app.yaml`.

### Pipeline + DQ + Dashboards

- **Deploy**: `databricks bundle deploy` (pipeline, job, dashboards).
- **Run pipeline**: `databricks bundle run butterfly_etl`.
- **Run full job**: `databricks bundle run butterfly_pipeline_and_dq` (needs `variables.warehouse_id` in `databricks.yml` or target).

### Local development (app only)

**1. Set environment** (required for app to use Lakebase / LLM / Genie):

```bash
# From repo root: copy template, edit .env with your PGUSER, PGPASSWORD, etc.
cp env.template .env
# Then load into shell (choose one):
export $(grep -v '^#' .env | xargs)   # simple; breaks on multiline values
# or
set -a && source .env && set +a       # bash/zsh, supports more .env formats
```

**2. Start backend**

```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

**3. Start frontend** (separate terminal)

```bash
cd app/frontend
npm install && npm run dev
# Open http://localhost:5173 (Vite proxies /api to :8000)
```

Without `PGUSER`/`PGPASSWORD` the app serves mock actions/contacts. Without `DATABRICKS_HOST` and `DATABRICKS_TOKEN`, LLM and Genie tabs show "not configured."

---

## Directory Structure

```text
jnj-butterfly-demo/
├── ARCHITECTURE.md           # This file
├── README.md                 # Project and run instructions
├── databricks.yml            # Bundle root: name, include, variables, targets (dev/prod)
├── env.template              # Env var template for local dev
├── .env                      # Local env (gitignored); copy from env.template
├── .gitignore                # Root gitignore (e.g. .env)
│
├── app/                      # Next Best Action web app
│   ├── app.py                # FastAPI app, routers, static SPA
│   ├── app.yaml              # Databricks App env (PG*, GENIE_SPACE_ID valueFrom)
│   ├── requirements.txt      # fastapi, uvicorn, asyncpg, databricks-sdk, openai, aiohttp
│   ├── README.md             # App run and deploy
│   ├── server/
│   │   ├── config.py         # All config from os.environ
│   │   ├── db.py             # asyncpg pool (or None if no PG creds)
│   │   ├── databricks_auth.py # Workspace host + token (env or SDK)
│   │   ├── llm.py            # Foundation Model API for NBA/email
│   │   └── routes/
│   │       ├── actions.py    # /api/actions — list, get, patch
│   │       ├── contacts.py   # /api/contacts — list, detail, nba, generate, patch
│   │       └── genie.py      # /api/genie — status, ask (Genie Conversation API)
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── App.tsx       # Tabs: NBA (contacts + detail + Genie)
│   │   │   ├── main.tsx
│   │   │   └── types.ts
│   │   ├── package.json
│   │   ├── vite.config.ts    # proxy /api → localhost:8000
│   │   └── dist/             # Built SPA (served by FastAPI)
│   └── setup/                # Lakebase one-time setup
│       ├── .env.example      # PGUSER, PGPASSWORD, optional Databricks/Genie
│       ├── setup_lakebase.py
│       ├── seed_contact_queue.py
│       ├── lakebase_contact_queue_ddl.sql
│       └── README.md
│
├── resources/                # Databricks Asset Bundle resources
│   ├── butterfly_etl.pipeline.yml
│   ├── butterfly_jobs.yml     # Job: pipeline → DQ → dashboard refresh
│   ├── butterfly_dashboards.yml
│   └── next_best_action_app.app.yml  # App + Genie space resource
│
├── src/butterfly_etl/transformations/
│   ├── bronze/
│   ├── silver/
│   └── gold/
│
├── setup/                    # UC and synthetic data (outside app)
│   ├── 01_create_infrastructure.sql
│   └── generate_synthetic_data.py
│
├── monitoring/
│   ├── create_data_quality_monitors.py
│   └── dq_reporting.sql
│
├── dashboards/               # Dashboard JSON and query validation
│   ├── customer360_dashboard.json
│   ├── data_quality_dashboard.json
│   └── validate_queries.sql
│
└── .claude/                  # Commands, skills (architecture, local-dev, etc.)
```
