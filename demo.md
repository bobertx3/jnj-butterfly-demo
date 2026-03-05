# Butterfly Demo - Lines of Work

Use this as your demo script and checklist.

## 1) Lakeflow Job

- Show the `butterfly_etl` pipeline/update history and last successful run.
- Walk through Bronze -> Silver -> Gold flow at a high level.
- Highlight key Gold outputs:
  - `bx4.butterfly.gold_customer_360`
  - KPI and performance materialized views used by dashboards.
- Point out operational reliability:
  - scheduled/triggered runs
  - rerun behavior
  - monitoring signals.

## 2) Unity Catalog

### Objects (Structured + Unstructured)

- Structured objects:
  - tables/views in `bx4.butterfly` (especially Gold layer).
- Unstructured objects:
  - call log PDFs in UC Volumes (`/Volumes/.../call_logs`).
- Explain how both are governed under the same catalog/schema model.

### AI Definitions

- Show governed AI-related definitions and assets, such as:
  - registered model example (`next_best_action_agent`)
  - SQL/AI functions used in workflows where applicable.
- Emphasize discoverability and governance in UC.

### DQ

- Show data quality expectations and monitor outputs tied to pipeline tables.
- Explain where quality checks run and where results are surfaced.

### Lineage

- Demonstrate lineage from raw/bronze sources to `gold_customer_360`.
- Show downstream dependencies:
  - dashboards
  - app usage paths.

### Permissions and Securing Data (`bx4.butterfly.gold_customer_360`)

- Show table/view-level access controls and governed sharing patterns.
- Demonstrate column-level protection on `won_amount`:
  - masking behavior for `robert.leach@databricks.com`
  - group-aware policy via `jnj_cxm_business`.
- Explain why this is important for role-based data access in customer analytics.

### Metric Views

- Show the governed metric view:
  - `bx4.butterfly.gold_customer_kpis_metrics`
  - source: `bx4.butterfly.gold_customer_kpis_daily`
- Demonstrate reusable KPI logic:
  - `Customer Count`
  - `Total Net Sales`
  - `Total Open Pipeline`
  - `Engagement Rate`
- Run a quick SQL example using `MEASURE(...)` to show consistent metric definitions across consumers.

## 3) Data Quality Lineage

- Connect quality checks to lineage:
  - where defects are detected
  - which downstream assets are impacted.
- Show how this supports trust and faster root-cause analysis.

## 4) Metric Views

- Explain why metric views matter:
  - centralized KPI semantics
  - consistent numbers across dashboards, Genie, and SQL.
- Demo querying `bx4.butterfly.gold_customer_kpis_metrics` with:
  - dimensions: `Metric Date`, `Metric Month`
  - measures via `MEASURE(...)`.
- Connect this to governance: one metric definition, many consumers.

## 5) Genie Spaces

- Open Genie Space and ask business-facing questions.
- Show generated SQL + result traceability to governed UC objects.
- Emphasize analyst self-service on top of curated Gold data.

## 6) Published Power BI (`bx4.butterfly.gold_customer_360`)

- Show the published Power BI report/dataset built from `bx4.butterfly.gold_customer_360`.
- Walk through key business views:
  - account performance
  - product/company rollups
  - pipeline and win metrics.
- Explain refresh and governance model:
  - governed source in Unity Catalog
  - consistent KPI definitions across BI tools.
- Highlight security behavior in BI consumption:
  - masked `won_amount` behavior for restricted viewers
  - role/group-based access alignment with UC policies.

## 7) Databricks Apps (Backed by Lakebase)

- Demo the app UX and key business workflows.
- Explain architecture:
  - app frontend/backend
  - Lakebase for operational serving needs
  - governed analytics data from UC.
- Tie back to real user value:
  - faster account insight
  - next-best-action support
  - secure enterprise deployment model.

## Optional Closeout Slide / Talking Points

- Single governed platform across data engineering, governance, AI, BI, and apps.
- Security and compliance built-in (not bolted on).
- Faster path from raw data to business action.
