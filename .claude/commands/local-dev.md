Set up local development environment files for this project.

## Instructions

1. Create an `env.template` file at the project root with the following content (values left blank as placeholders):

```
# ── Local development ─────────────────────────────────────────────
DATABRICKS_PROFILE=

# ── Data location ────────────────────────────────────────────────
CATALOG=
SCHEMA=

# ── SQL Warehouse ────────────────────────────────────────────────
DATABRICKS_WAREHOUSE_ID=

# ── AI / Genie ───────────────────────────────────────────────────
SERVING_ENDPOINT=
GENIE_SPACE_ID=

# ── Deployment only ──────────────────────────────────────────────
APP_NAME=
VOLUME=
TABLE=
VS_INDEX=
DATABRICKS_TOKEN=
```

2. Create a `.env` file at the project root with the actual default values:

```
# ── Local development ─────────────────────────────────────────────
DATABRICKS_PROFILE=DEFAULT

# ── Data location ────────────────────────────────────────────────
CATALOG=bx4
SCHEMA=eo_analytics_plane

# ── SQL Warehouse ────────────────────────────────────────────────
DATABRICKS_WAREHOUSE_ID=

# ── AI / Genie ───────────────────────────────────────────────────
SERVING_ENDPOINT=
GENIE_SPACE_ID=

# ── Deployment only ──────────────────────────────────────────────
APP_NAME=
VOLUME=raw_landing
TABLE=
VS_INDEX=
DATABRICKS_TOKEN=
```

3. Ensure `.env` is listed in `.gitignore` so secrets are never committed. If `.gitignore` does not exist, create one that includes `.env`.

4. All application code should read configuration from environment variables (e.g., `os.environ` in Python, `process.env` in Node.js) so that `.env` drives local dev and app configuration drives deployment.
