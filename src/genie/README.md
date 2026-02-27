# Genie source for Butterfly schema

This folder is the **source for the Butterfly Genie space**: table list, description, and sample questions.

**Created space:** Butterfly Analytics  
**Space ID:** `01f113a87bfc17ca8e758c57f12e5a06`  
**Warehouse:** Serverless Starter Warehouse

## Config

- **`butterfly_genie_config.yaml`** – Defines display name, tables, description, and sample questions for the "Butterfly Analytics" Genie space.

## Creating or updating the Genie space

1. **Via MCP** (if Databricks MCP is available): use the `create_or_update_genie` tool with the values from `butterfly_genie_config.yaml`.

2. **Via script**: from the repo root, with a Databricks-configured environment:
   ```bash
   python src/genie/create_genie_space.py
   ```
   The script reads `butterfly_genie_config.yaml`, builds the Genie API payload, and creates or updates the space (requires `databricks-sdk` and a configured workspace).

3. **Via UI**: In Databricks, go to Genie, create a space, and add the tables and sample questions from the config.

## Key tables included

| Table | Layer | Purpose |
|-------|--------|--------|
| silver_account | Silver | Account master (region, segment, tier) |
| silver_contact | Silver | Contact master |
| silver_transactions | Silver | Transaction history (net_sales, gross_profit) |
| silver_opportunities | Silver | Pipeline (stage_name, amount) |
| gold_customer_360 | Gold | Account rollups (lifetime_net_sales, open_pipeline_amount) |
| gold_region_performance | Gold | Regional KPIs |
| gold_product_company_brand_performance | Gold | Product company/brand metrics |
