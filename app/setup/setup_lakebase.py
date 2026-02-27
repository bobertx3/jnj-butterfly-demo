"""
Create next_best_action table in Lakebase and seed with sample data.

Run with PGUSER and PGPASSWORD set (from env, local .env, or secret scope).
Uses same host/database as app: ep-wandering-scene-d2440hao / batch_release_db.
Loads .env from script directory or app root if present (local profile).
"""

from __future__ import annotations

import asyncio
import os

# Load local profile (.env) if present
_script_dir = os.path.dirname(os.path.abspath(__file__))
_env_file = os.path.join(_script_dir, ".env")
if not os.path.isfile(_env_file):
    _env_file = os.path.join(os.path.dirname(_script_dir), ".env")
if os.path.isfile(_env_file):
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k in ("PGUSER", "PGPASSWORD", "PGHOST", "PGPORT", "PGDATABASE", "PGSCHEMA") and k not in os.environ:
                    os.environ[k] = v
import random
from datetime import date, datetime, timedelta, timezone

# Use same env as app
os.environ.setdefault("PGHOST", "ep-wandering-scene-d2440hao.database.us-east-1.cloud.databricks.com")
os.environ.setdefault("PGPORT", "5432")
os.environ.setdefault("PGDATABASE", "batch_release_db")

import asyncpg

TABLE_NAME = "next_best_action"
# Use existing public schema in batch_release_db; no schema creation.
SCHEMA_NAME = "public"
SEED_ROWS = 120
SEED = 42

# Action types aligned to Butterfly / J&J MedTech
ACTION_TYPES = [
    ("product_demo", "Schedule product demo", "Offer a live demo of the requested product line."),
    ("follow_up_visit", "Schedule follow-up visit", "In-person or virtual visit to advance the opportunity."),
    ("webinar_invite", "Send webinar invitation", "Invite contact to an upcoming specialty webinar."),
    ("case_follow_up", "Follow up on open case", "Check in on open support case and ensure resolution."),
    ("opportunity_nurture", "Nurture opportunity", "Send relevant content and schedule next touchpoint."),
    ("consent_refresh", "Refresh consent preferences", "Confirm marketing and contact preferences."),
]
PRIORITIES = ["high", "medium", "low"]
STATUSES = ["pending", "in_progress", "completed", "dismissed"]


def get_connection_params():
    return {
        "host": os.environ.get("PGHOST"),
        "port": int(os.environ.get("PGPORT", "5432")),
        "database": os.environ.get("PGDATABASE"),
        "user": os.environ.get("PGUSER"),
        "password": os.environ.get("PGPASSWORD"),
        "ssl": "require",
    }


async def create_schema_and_table(conn: asyncpg.Connection) -> None:
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS "{SCHEMA_NAME}"."{TABLE_NAME}" (
            id SERIAL PRIMARY KEY,
            account_id VARCHAR(32) NOT NULL,
            contact_id VARCHAR(32),
            action_type VARCHAR(64) NOT NULL,
            title VARCHAR(256) NOT NULL,
            description TEXT,
            priority VARCHAR(16) NOT NULL DEFAULT 'medium',
            status VARCHAR(24) NOT NULL DEFAULT 'pending',
            due_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    print(f'[setup] Schema "{SCHEMA_NAME}" and table "{TABLE_NAME}" ensured.')


def generate_seed_rows() -> list[tuple]:
    """Generate seed rows aligned to Butterfly account/contact IDs and action types."""
    random.seed(SEED)
    base_date = date.today()
    rows = []
    for i in range(SEED_ROWS):
        acc_idx = random.randint(1, 200)  # ACC-000001 .. ACC-000200
        contact_idx = random.randint(1, 800)  # CON-0000001 ..
        account_id = f"ACC-{acc_idx:06d}"
        contact_id = f"CON-{contact_idx:07d}" if random.random() > 0.3 else None
        action_type, title, description = random.choice(ACTION_TYPES)
        priority = random.choice(PRIORITIES)
        status = random.choices(STATUSES, weights=[0.5, 0.2, 0.2, 0.1])[0]
        due_date = base_date + timedelta(days=random.randint(-7, 21))
        created = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 14))
        rows.append((account_id, contact_id, action_type, title, description, priority, status, due_date, created))
    return rows


async def seed_table(conn: asyncpg.Connection, truncate: bool = True) -> int:
    if truncate:
        try:
            await conn.execute(f'TRUNCATE TABLE "{SCHEMA_NAME}"."{TABLE_NAME}" RESTART IDENTITY CASCADE')
        except asyncpg.InsufficientPrivilegeError:
            pass  # append if no TRUNCATE permission
    rows = generate_seed_rows()
    for r in rows:
        await conn.execute(
            f'''
            INSERT INTO "{SCHEMA_NAME}"."{TABLE_NAME}"
            (account_id, contact_id, action_type, title, description, priority, status, due_date, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9)
            ''',
            r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8],
        )
    print(f"[setup] Seeded {len(rows)} rows into {SCHEMA_NAME}.{TABLE_NAME}.")
    return len(rows)


def _parse_args() -> bool:
    import sys
    return "--seed-only" in sys.argv


async def main() -> None:
    seed_only = _parse_args()
    params = get_connection_params()
    if not params.get("user") or not params.get("password"):
        print("Set PGUSER and PGPASSWORD (or bind from secret scope) and re-run.")
        raise SystemExit(1)
    conn = await asyncpg.connect(**params)
    try:
        if not seed_only:
            await create_schema_and_table(conn)
        n = await seed_table(conn)
        print(f"[setup] Done. Total rows: {n}.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
