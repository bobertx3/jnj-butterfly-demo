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

Then in **Databricks** > **Apps** > **next-best-action-prod** > **Edit**:

- Add **Environment** entries for `PGUSER` and `PGPASSWORD` from your secret scope (e.g. scope with keys `PGUSER` / `PGPASSWORD`).
- Save and redeploy if needed.

## UI

- **J&J theme**: red `#D71500`, white, gray; clean and minimal.
- **Actions list**: title, description, account/contact, due date, priority, status.
- **Actions**: Start, Complete, Dismiss (updates status in Lakebase).
