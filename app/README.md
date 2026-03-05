# Next Best Action — Databricks App

Minimal **Next Best Action** app for Johnson & Johnson MedTech: list and update recommended actions stored in **Lakebase Autoscale** (PostgreSQL).

## Stack

- **Backend**: FastAPI, asyncpg
- **Frontend**: React, Vite, Tailwind CSS (J&J theme)
- **Database**: Lakebase Autoscale — `batch_release_db` on `ep-wandering-scene-d2440hao.database.us-east-1.cloud.databricks.com`

## Database

- Table: `app.next_best_action` (created and seeded by `setup/setup_lakebase.py`).
- Credentials: use secret scope for `PGUSER` and `PGPASSWORD` (e.g. `lakebase-native-user` / `lakebase-native-password` with keys `PGUSER` / `PGPASSWORD`).

## Setup (one-time)

1. Ensure Lakebase DB is reachable and you have credentials.
2. Set env or use secret scope:
   - `PGUSER`, `PGPASSWORD`
   - Optional: `PGHOST`, `PGPORT`, `PGDATABASE` (defaults in `server/config.py`).
3. Run:

   ```bash
   cd app/setup
   pip install asyncpg
   export PGUSER=... PGPASSWORD=...
   python setup_lakebase.py
   ```

See `setup/README.md` for more options (e.g. Databricks notebook + secrets).

## Local run

```bash
# Backend
cd app
pip install -r requirements.txt
export PGUSER=... PGPASSWORD=...
uvicorn app:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install && npm run dev
# Open http://localhost:5173 (proxies /api to 8000)
```

## Build for deployment

```bash
cd app/frontend
npm install
npm run build
# frontend/dist is served by FastAPI in production
```

## Deploy via bundle

From repo root:

```bash
databricks bundle deploy -t prod
databricks bundle run next_best_action_app -t prod
```

**Lakebase credentials (required for real data):** The app expects two **Secret resources** with keys **`lakebase-native-user`** and **`lakebase-native-password`** (mapped to env vars `PGUSER` and `PGPASSWORD` in `app.yaml`). After deploy:

1. Create a secret scope and store the Lakebase user and password.
2. In **Databricks** > **Apps** > **next-best-action-prod** > **Edit** > **Configure** > **Resources**: add two Secret resources with keys **`lakebase-native-user`** and **`lakebase-native-password`**, each pointing to your scope + secret. Permission: **Can read**.
3. Save. The app injects them as `PGUSER` and `PGPASSWORD` at runtime.

Without these resources, the app falls back to mock data.

## Genie (Sales data Q&A tab)

The **Sales data Q&A** tab uses a **Genie space** for natural language questions over your data. To enable it:

1. In Databricks, open your app and go to **Configure** > **Resources**.
2. Click **Add resource** and choose **Genie space**.
3. Select your Genie space (e.g. Butterfly Analytics).
4. Set the resource **key** to **`genie-space`** (must match `valueFrom` in `app.yaml`).
5. Save and reopen the app.

The app reads the space ID from this resource so it runs with access to that Genie space in the same workspace.

## LLM (NBA + email generation)

- **Generate NBA** and **Generate Email Draft** call the **Databricks Foundation Model API** when `DATABRICKS_HOST` and `DATABRICKS_TOKEN` are set.
- Default model: `databricks-claude-sonnet-4-6`; override with `DATABRICKS_FM_ENDPOINT`.
- Prompts use contact context (role, institution, signals) and J&J MedTech terminology (Ethicon, J&J Vision, OTTAVA, Abiomed). If the LLM is not configured or the call fails, the app falls back to MedTech-flavored static copy keyed by role/specialty.

## UI

- **J&J MedTech theme**: red `#D71500`, white, gray; copy aligned to surgical, vision, and heart recovery portfolios.
- **Prioritized Contact Queue**: HCPs ranked by priority, intent, recency; filters (high priority, at risk, intent spike, needs outreach).
- **Next Best Action**: AI-generated recommendation and email draft (Databricks LLM or fallback).
- **Actions list**: title, description, account/contact, due date, priority, status.
- **Actions**: Start, Complete, Dismiss (updates status in Lakebase).
