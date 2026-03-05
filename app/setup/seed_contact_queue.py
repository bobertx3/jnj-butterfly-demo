"""
Seed public.contact_queue and public.nba_recommendation for the Prioritized Contact Queue UI.
Content is J&J MedTech–only (Ethicon, J&J Vision, OTTAVA, Abiomed): roles, institutions, and NBA copy.
Run after applying lakebase_contact_queue_ddl.sql. Uses same .env as setup_lakebase.py.
"""

from __future__ import annotations

import asyncio
import os
import random
import sys

# Load .env like setup_lakebase
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
                if k in ("PGUSER", "PGPASSWORD", "PGHOST", "PGPORT", "PGDATABASE") and k not in os.environ:
                    os.environ[k] = v

os.environ.setdefault("PGHOST", "ep-wandering-scene-d2440hao.database.us-east-1.cloud.databricks.com")
os.environ.setdefault("PGPORT", "5432")
os.environ.setdefault("PGDATABASE", "batch_release_db")

import asyncpg

SEED = 42
NAMES = [
    ("Kai", "Price"), ("Reese", "Rivera"), ("Jordan", "Morris"), ("Hayden", "Diaz"), ("Casey", "Diaz"),
    ("Morgan", "Lee"), ("Riley", "Clark"), ("Avery", "Lewis"), ("Quinn", "Hall"), ("Skyler", "Young"),
]
# J&J MedTech: Ethicon (surgery), J&J Vision (ophthalmology), OTTAVA (robotic), Abiomed (heart)
ROLES = [
    "General Surgeon", "Cardiovascular Surgeon", "Ophthalmologist", "Refractive Surgeon",
    "Interventional Cardiologist", "Surgical Lead", "OR Director", "Cath Lab Director",
    "Bariatric Surgeon", "Gynecological Surgeon",
]
INSTITUTIONS = [
    "Evergreen Surgical Center", "Metro Heart & Vascular Institute", "Northview Ophthalmology Associates",
    "Central Surgical Institute", "Valley Regional Hospital", "Summit Cardiology",
    "Lakeside Medical Center", "Ridgeview Eye Institute", "Pioneer Robotic Surgery Program",
]
RISK_LEVELS = ["High", "Medium", "Low"]
CHANNELS = ["Email", "Phone", "In-Person"]
# MedTech product/therapy context for NBA copy
MEDTECH_CONTEXTS = [
    ("surgical stapling and wound closure adoption", "ECHELON and STRATAFIX"),
    ("energy sealing and dissection portfolio", "HARMONIC and MEGADYNE"),
    ("IOL and refractive procedure volume", "TECNIS SYMFONY and ELITA"),
    ("contact lens fitting and ACUVUE adoption", "ACUVUE OASYS and ACUVUE VITA"),
    ("robotic surgery program expansion", "OTTAVA Robotic System"),
    ("heart recovery and Impella utilization", "Impella CP and Impella 5.5"),
]
FOLLOW_UP_OBJECTIVES = [
    "Confirm adoption blockers and align next in-service training",
    "Share outcomes resource and schedule short clinical follow-up",
    "Review formulary/access questions and identify next support step",
    "Plan brief check-in to discuss utilization trends and next actions",
]


def get_connection_params():
    return {
        "host": os.environ.get("PGHOST"),
        "port": int(os.environ.get("PGPORT", "5432")),
        "database": os.environ.get("PGDATABASE"),
        "user": os.environ.get("PGUSER"),
        "password": os.environ.get("PGPASSWORD"),
        "ssl": "require",
    }


async def seed_contact_queue(conn: asyncpg.Connection) -> int:
    random.seed(SEED)
    try:
        await conn.execute('TRUNCATE TABLE public.contact_queue RESTART IDENTITY CASCADE')
    except asyncpg.InsufficientPrivilegeError:
        pass
    rows = []
    for i in range(50):
        first, last = NAMES[i % len(NAMES)]
        name = f"{first} {last}"
        if i >= len(NAMES):
            name = f"{first} {last} {i}"
        contact_id = f"HCP-{i+1:05d}"
        priority_score = round(random.uniform(60, 95), 1)
        intent_score = random.choice([80, 90, 100, 100, 100])
        risk_level = random.choices(RISK_LEVELS, weights=[0.3, 0.4, 0.3])[0]
        last_touch_days = random.randint(7, 60)
        trx_volume_3m = random.randint(20, 80)
        nrx_volume_3m = random.randint(1, 10)
        site_visits = random.randint(2, 12)
        webinar_signups = random.randint(0, 5)
        rx_growth = round(random.uniform(-40, 25), 1)
        interaction_channel = random.choice(CHANNELS)
        interaction_days_ago = random.randint(3, 45)
        context, brands = MEDTECH_CONTEXTS[i % len(MEDTECH_CONTEXTS)]
        interaction_summary = (
            f"Last {interaction_channel.lower()} follow-up covered {context} with focus on {brands}."
        )
        follow_up_objective = FOLLOW_UP_OBJECTIVES[i % len(FOLLOW_UP_OBJECTIVES)]
        await conn.execute(
            """
            INSERT INTO public.contact_queue
            (contact_id, name, role_specialty, institution, priority_score, intent_score, risk_level,
             preferred_channel, last_touch_days, last_interaction_channel, last_interaction_date,
             last_interaction_summary, last_products_discussed, next_follow_up_objective,
             trx_volume_3m, nrx_volume_3m, site_visits, webinar_signups, rx_growth_3m_pct,
             territory_id, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW() - ($11 * INTERVAL '1 day'),
                    $12, $13, $14, $15, $16, $17, $18, $19, $20, NOW())
            ON CONFLICT (contact_id) DO UPDATE SET
            name=EXCLUDED.name, role_specialty=EXCLUDED.role_specialty, institution=EXCLUDED.institution,
            priority_score=EXCLUDED.priority_score, intent_score=EXCLUDED.intent_score, risk_level=EXCLUDED.risk_level,
            preferred_channel=EXCLUDED.preferred_channel, last_touch_days=EXCLUDED.last_touch_days,
            last_interaction_channel=EXCLUDED.last_interaction_channel, last_interaction_date=EXCLUDED.last_interaction_date,
            last_interaction_summary=EXCLUDED.last_interaction_summary, last_products_discussed=EXCLUDED.last_products_discussed,
            next_follow_up_objective=EXCLUDED.next_follow_up_objective,
            trx_volume_3m=EXCLUDED.trx_volume_3m, nrx_volume_3m=EXCLUDED.nrx_volume_3m,
            site_visits=EXCLUDED.site_visits, webinar_signups=EXCLUDED.webinar_signups,
            rx_growth_3m_pct=EXCLUDED.rx_growth_3m_pct, updated_at=NOW()
            """,
            contact_id, name, random.choice(ROLES), random.choice(INSTITUTIONS),
            priority_score, intent_score, risk_level, random.choice(CHANNELS),
            last_touch_days, interaction_channel, interaction_days_ago, interaction_summary, brands,
            follow_up_objective, trx_volume_3m, nrx_volume_3m, site_visits, webinar_signups,
            rx_growth, "TERRITORY-001",
        )
        rows.append(contact_id)
    print(f"[seed] contact_queue: {len(rows)} rows.")
    return len(rows)


async def seed_nba_recommendations(conn: asyncpg.Connection) -> int:
    random.seed(SEED + 1)
    for i in range(50):
        contact_id = f"HCP-{i+1:05d}"
        context, brands = MEDTECH_CONTEXTS[i % len(MEDTECH_CONTEXTS)]
        rec = (
            f"Contact is high-priority with strong intent in {context}. "
            f"Recommended: personalized re-engagement and follow-up on {brands}."
        )
        subject = "MedTech follow-up: 15-min check-in this week?"
        body = (
            f"I'm reaching out regarding your interest in {context}. "
            f"We've seen strong engagement with {brands} in your region and would like to schedule a brief check-in."
        )
        await conn.execute(
            """
            INSERT INTO public.nba_recommendation (contact_id, recommendation_text, email_draft_subject, email_draft_body, generated_at, updated_at)
            VALUES ($1, $2, $3, $4, NOW(), NOW())
            ON CONFLICT (contact_id) DO UPDATE SET
            recommendation_text=EXCLUDED.recommendation_text,
            email_draft_subject=EXCLUDED.email_draft_subject,
            email_draft_body=EXCLUDED.email_draft_body,
            generated_at=NOW(), updated_at=NOW()
            """,
            contact_id, rec, subject, body,
        )
    print("[seed] nba_recommendation: 50 rows.")
    return 50


async def main() -> None:
    params = get_connection_params()
    if not params.get("user") or not params.get("password"):
        print("Set PGUSER and PGPASSWORD in .env and re-run.")
        raise SystemExit(1)
    conn = await asyncpg.connect(**params)
    try:
        n1 = await seed_contact_queue(conn)
        n2 = await seed_nba_recommendations(conn)
        print(f"[seed] Done. contact_queue={n1}, nba_recommendation={n2}.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
