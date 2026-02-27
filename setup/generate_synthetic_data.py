"""Generate Butterfly synthetic CSV inputs in Unity Catalog volume."""

from datetime import date, datetime, timedelta
import random

from pyspark.sql import SparkSession


# =============================================================================
# Configuration
# =============================================================================
CATALOG = "bx4"
SCHEMA = "butterfly"
RAW_VOLUME = "raw_landing"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{RAW_VOLUME}"

N_ACCOUNTS = 2000
N_PRODUCTS = 240
N_EMPLOYEES = 350
N_ACTIVITIES = 30000
N_TRANSACTIONS = 50000
N_CASES = 18000
N_OPPORTUNITIES = 12000
CONTACTS_PER_ACCOUNT_MIN = 1
CONTACTS_PER_ACCOUNT_MAX = 5
SEED = 42

REGIONS = ["NA", "EMEA", "APAC", "JP", "LATAM", "CA"]
SEGMENTS = ["Academic", "Hospital", "Distributor", "Private Practice", "Government"]
TIERS = ["Strategic", "Enterprise", "Growth", "Long Tail"]
ACTIVITY_TYPE = ["visit", "email", "call", "webinar", "demo", "support_followup"]
CASE_CATEGORY = ["billing", "clinical", "shipping", "technical", "contract"]
CASE_STATUS = ["open", "in_progress", "resolved", "closed"]
CONSENT_CHANNEL = ["email", "sms", "phone"]
OPP_STAGE = [
    "prospecting",
    "qualification",
    "value_proposition",
    "proposal",
    "negotiation",
    "closed_won",
    "closed_lost",
]

# Portfolio model aligned to J&J MedTech business lines called out in request:
# Ethicon, J&J Vision, OTTAVA, and Abiomed.
MEDTECH_PORTFOLIO = [
    {
        "company": "Ethicon",
        "platform": "Surgical Stapling",
        "brands": ["ECHELON", "PROXIMATE", "ENDOPATH"],
        "price_range": (180.0, 2600.0),
    },
    {
        "company": "Ethicon",
        "platform": "Energy Sealing and Dissecting",
        "brands": ["ENSEAL X1", "HARMONIC", "MEGADYNE", "GEN11"],
        "price_range": (220.0, 3200.0),
    },
    {
        "company": "Ethicon",
        "platform": "Wound Closure and Biosurgery",
        "brands": ["STRATAFIX", "ETHICON PLUS", "VICRYL", "SURGICEL", "VISTASEAL"],
        "price_range": (20.0, 1400.0),
    },
    {
        "company": "J&J Vision",
        "platform": "Contact Lenses",
        "brands": ["ACUVUE OASYS", "ACUVUE MOIST", "ACUVUE VITA", "ACUVUE MAX"],
        "price_range": (12.0, 180.0),
    },
    {
        "company": "J&J Vision",
        "platform": "IOL and Refractive",
        "brands": ["TECNIS SYMFONY", "TECNIS SYNERGY", "TECNIS EYHANCE", "ELITA", "VERITAS"],
        "price_range": (240.0, 18000.0),
    },
    {
        "company": "OTTAVA",
        "platform": "Robotic Surgery",
        "brands": ["OTTAVA Robotic System", "OTTAVA Instruments"],
        "price_range": (4500.0, 25000.0),
    },
    {
        "company": "Abiomed",
        "platform": "Heart Recovery",
        "brands": ["Impella 2.5", "Impella CP", "Impella 5.5", "Automated Impella Controller"],
        "price_range": (3500.0, 30000.0),
    },
]


def rand_date(start_dt: date, end_dt: date) -> date:
    span_days = (end_dt - start_dt).days
    return start_dt + timedelta(days=random.randint(0, max(0, span_days)))


def maybe_null(value, probability=0.0):
    if random.random() < probability:
        return None
    return value


def main() -> None:
    random.seed(SEED)
    spark = SparkSession.builder.getOrCreate()

    # Catalog and volume are pre-provisioned by workspace admins.
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=180)

    # Foundational: account
    accounts = []
    for i in range(N_ACCOUNTS):
        account_id = f"ACC-{i + 1:06d}"
        accounts.append(
            {
                "account_id": account_id,
                "account_name": f"Account {i + 1}",
                "region": random.choice(REGIONS),
                "segment": random.choice(SEGMENTS),
                "tier": random.choices(TIERS, weights=[0.08, 0.2, 0.35, 0.37])[0],
                "created_date": rand_date(start_date - timedelta(days=540), start_date).isoformat(),
                "is_active": random.random() > 0.03,
            }
        )

    # Foundational: contact
    contacts = []
    c_idx = 1
    for account in accounts:
        for _ in range(random.randint(CONTACTS_PER_ACCOUNT_MIN, CONTACTS_PER_ACCOUNT_MAX)):
            region = account["region"]
            email = f"contact{c_idx}@example.com"
            contacts.append(
                {
                    "contact_id": f"CON-{c_idx:07d}",
                    "account_id": account["account_id"],
                    "first_name": f"First{c_idx}",
                    "last_name": f"Last{c_idx}",
                    # Inject light DQ issues for monitoring demos.
                    "email": maybe_null(email, probability=0.01),
                    "job_title": random.choice(["Surgeon", "Procurement Lead", "Nurse Manager", "CFO", "IT Admin"]),
                    "region": region,
                    "created_date": rand_date(start_date - timedelta(days=365), end_date).isoformat(),
                }
            )
            c_idx += 1

    # Foundational: consent
    consents = []
    for contact in contacts:
        for channel in CONSENT_CHANNEL:
            consents.append(
                {
                    "consent_id": f"CNS-{len(consents) + 1:08d}",
                    "contact_id": contact["contact_id"],
                    "channel": channel,
                    "is_opted_in": random.random() > 0.25,
                    "consent_date": rand_date(start_date - timedelta(days=365), end_date).isoformat(),
                }
            )

    # Foundational: product catalog aligned to requested J&J MedTech portfolio.
    products = []
    for i in range(N_PRODUCTS):
        portfolio = random.choices(
            MEDTECH_PORTFOLIO,
            # Ethicon + Vision carry more SKU breadth; OTTAVA/Abiomed fewer SKUs.
            weights=[0.17, 0.17, 0.16, 0.16, 0.16, 0.08, 0.10],
        )[0]
        brand = random.choice(portfolio["brands"])
        min_price, max_price = portfolio["price_range"]
        products.append(
            {
                "product_id": f"PRD-{i + 1:05d}",
                "product_name": f"{brand} {random.choice(['Core', 'Plus', 'Advanced', 'Pro'])} {random.randint(1, 9)}",
                "product_family": portfolio["platform"],
                "product_company": portfolio["company"],
                "product_brand": brand,
                "unit_price": round(random.uniform(min_price, max_price), 2),
                "is_active": random.random() > 0.05,
            }
        )

    # Foundational: alignment/territory
    alignments = []
    for idx, region in enumerate(REGIONS):
        for t in range(1, 26):
            alignments.append(
                {
                    "territory_id": f"TER-{region}-{t:03d}",
                    "region": region,
                    "territory_name": f"{region}-Territory-{t}",
                    "is_active": True,
                }
            )

    # Foundational: employee
    employees = []
    for i in range(N_EMPLOYEES):
        region = random.choice(REGIONS)
        employees.append(
            {
                "employee_id": f"EMP-{i + 1:06d}",
                "employee_name": f"Employee {i + 1}",
                "region": region,
                "role": random.choice(["Sales Rep", "CSM", "Marketing Manager", "Service Agent", "Manager"]),
                "territory_id": random.choice([a["territory_id"] for a in alignments if a["region"] == region]),
                "is_active": random.random() > 0.06,
            }
        )

    account_ids = [a["account_id"] for a in accounts]
    product_ids = [p["product_id"] for p in products]
    product_price_map = {p["product_id"]: p["unit_price"] for p in products}
    employee_ids = [e["employee_id"] for e in employees]
    contact_ids = [c["contact_id"] for c in contacts]

    # Foundational: transactional data
    transactions = []
    for i in range(N_TRANSACTIONS):
        quantity = random.randint(1, 5)
        selected_product_id = random.choice(product_ids)
        unit_price = float(product_price_map[selected_product_id])
        discount_pct = random.choice([0, 0, 0, 0.05, 0.1, 0.15])
        gross_sales = quantity * unit_price
        net_sales = gross_sales * (1 - discount_pct)
        gross_profit = net_sales * random.uniform(0.35, 0.7)
        transactions.append(
            {
                "transaction_id": f"TRX-{i + 1:08d}",
                "account_id": random.choice(account_ids),
                "product_id": selected_product_id,
                "employee_id": random.choice(employee_ids),
                "invoice_date": rand_date(start_date, end_date).isoformat(),
                "quantity": quantity,
                "gross_sales": round(gross_sales, 2),
                "net_sales": round(net_sales, 2),
                "gross_profit": round(gross_profit, 2),
                "currency_code": "USD",
            }
        )

    # Experience domains: activities
    activities = []
    for i in range(N_ACTIVITIES):
        activities.append(
            {
                "activity_id": f"ACT-{i + 1:08d}",
                "account_id": random.choice(account_ids),
                "contact_id": random.choice(contact_ids),
                "employee_id": random.choice(employee_ids),
                "activity_type": random.choice(ACTIVITY_TYPE),
                "activity_date": rand_date(start_date, end_date).isoformat(),
                "is_successful": random.random() > 0.12,
            }
        )

    # Experience domains: opportunities
    opportunities = []
    for i in range(N_OPPORTUNITIES):
        stage = random.choices(OPP_STAGE, weights=[0.1, 0.18, 0.18, 0.2, 0.16, 0.1, 0.08])[0]
        close_date = rand_date(start_date, end_date + timedelta(days=90))
        opportunities.append(
            {
                "opportunity_id": f"OPP-{i + 1:08d}",
                "account_id": random.choice(account_ids),
                "owner_employee_id": random.choice(employee_ids),
                "stage_name": stage,
                "amount": round(random.lognormvariate(8.4, 0.9), 2),
                "created_date": rand_date(start_date - timedelta(days=120), end_date).isoformat(),
                "close_date": close_date.isoformat(),
            }
        )

    # Experience domains: cases
    cases = []
    for i in range(N_CASES):
        created = rand_date(start_date, end_date)
        status = random.choices(CASE_STATUS, weights=[0.16, 0.2, 0.24, 0.4])[0]
        if status in ("resolved", "closed"):
            resolved = created + timedelta(hours=random.randint(4, 120))
            resolved_str = datetime.combine(created, datetime.min.time()) + timedelta(hours=random.randint(6, 96))
            resolved_at = resolved_str.isoformat()
        else:
            resolved_at = None
        cases.append(
            {
                "case_id": f"CAS-{i + 1:08d}",
                "account_id": random.choice(account_ids),
                "contact_id": random.choice(contact_ids),
                "owner_employee_id": random.choice(employee_ids),
                "category": random.choice(CASE_CATEGORY),
                "status": status,
                "priority": random.choice(["critical", "high", "medium", "low"]),
                "created_at": datetime.combine(created, datetime.min.time()).isoformat(),
                "resolved_at": resolved_at,
            }
        )

    datasets = {
        "account": accounts,
        "contact": contacts,
        "consent": consents,
        "product": products,
        "alignment": alignments,
        "employee": employees,
        "transactions": transactions,
        "activities": activities,
        "opportunities": opportunities,
        "cases": cases,
    }

    for name, rows in datasets.items():
        df = spark.createDataFrame(rows)
        output_path = f"{VOLUME_PATH}/{name}"
        (
            df.coalesce(1)
            .write.mode("overwrite")
            .option("header", "true")
            .csv(output_path)
        )
        print(f"Wrote {name:14s} rows={len(rows):8d} path={output_path}")


if __name__ == "__main__":
    main()
