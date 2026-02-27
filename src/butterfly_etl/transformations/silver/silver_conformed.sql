CREATE OR REFRESH MATERIALIZED VIEW silver_account (
  CONSTRAINT account_pk_not_null EXPECT (account_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT account_region_valid EXPECT (region IN ('NA', 'EMEA', 'APAC', 'JP', 'LATAM', 'CA')) ON VIOLATION DROP ROW
)
AS
SELECT
  account_id,
  trim(account_name) AS account_name,
  region,
  segment,
  tier,
  CAST(created_date AS DATE) AS created_date,
  CAST(is_active AS BOOLEAN) AS is_active,
  _ingested_at
FROM bronze_account
QUALIFY ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_contact (
  CONSTRAINT contact_pk_not_null EXPECT (contact_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT contact_account_fk EXPECT (account_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT contact_email_present EXPECT (email IS NOT NULL) ON VIOLATION DROP ROW
)
AS
SELECT
  contact_id,
  account_id,
  trim(first_name) AS first_name,
  trim(last_name) AS last_name,
  lower(trim(email)) AS email,
  job_title,
  region,
  CAST(created_date AS DATE) AS created_date,
  _ingested_at
FROM bronze_contact
QUALIFY ROW_NUMBER() OVER (PARTITION BY contact_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_product (
  CONSTRAINT product_pk_not_null EXPECT (product_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT unit_price_positive EXPECT (unit_price > 0) ON VIOLATION DROP ROW,
  CONSTRAINT product_company_present EXPECT (product_company IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT product_brand_present EXPECT (product_brand IS NOT NULL) ON VIOLATION DROP ROW
)
AS
SELECT
  product_id,
  trim(product_name) AS product_name,
  trim(product_company) AS product_company,
  product_family,
  trim(product_brand) AS product_brand,
  CAST(unit_price AS DECIMAL(18, 2)) AS unit_price,
  CAST(is_active AS BOOLEAN) AS is_active,
  _ingested_at
FROM bronze_product
QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_employee (
  CONSTRAINT employee_pk_not_null EXPECT (employee_id IS NOT NULL) ON VIOLATION DROP ROW
)
AS
SELECT
  employee_id,
  employee_name,
  region,
  role,
  territory_id,
  CAST(is_active AS BOOLEAN) AS is_active,
  _ingested_at
FROM bronze_employee
QUALIFY ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_transactions (
  CONSTRAINT trx_pk_not_null EXPECT (transaction_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT trx_account_fk_not_null EXPECT (account_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT trx_amount_valid EXPECT (net_sales >= 0 AND gross_profit >= 0) ON VIOLATION DROP ROW
)
AS
SELECT
  transaction_id,
  account_id,
  product_id,
  employee_id,
  CAST(invoice_date AS DATE) AS invoice_date,
  CAST(quantity AS INT) AS quantity,
  CAST(gross_sales AS DECIMAL(18, 2)) AS gross_sales,
  CAST(net_sales AS DECIMAL(18, 2)) AS net_sales,
  CAST(gross_profit AS DECIMAL(18, 2)) AS gross_profit,
  currency_code,
  _ingested_at
FROM bronze_transactions
QUALIFY ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_activities (
  CONSTRAINT activity_pk_not_null EXPECT (activity_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT activity_type_valid EXPECT (
    activity_type IN ('visit', 'email', 'call', 'webinar', 'demo', 'support_followup')
  ) ON VIOLATION DROP ROW
)
AS
SELECT
  activity_id,
  account_id,
  contact_id,
  employee_id,
  activity_type,
  CAST(activity_date AS DATE) AS activity_date,
  CAST(is_successful AS BOOLEAN) AS is_successful,
  _ingested_at
FROM bronze_activities
QUALIFY ROW_NUMBER() OVER (PARTITION BY activity_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_opportunities (
  CONSTRAINT opportunity_pk_not_null EXPECT (opportunity_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT opportunity_amount_non_negative EXPECT (amount >= 0) ON VIOLATION DROP ROW
)
AS
SELECT
  opportunity_id,
  account_id,
  owner_employee_id,
  stage_name,
  CAST(amount AS DECIMAL(18, 2)) AS amount,
  CAST(created_date AS DATE) AS created_date,
  CAST(close_date AS DATE) AS close_date,
  _ingested_at
FROM bronze_opportunities
QUALIFY ROW_NUMBER() OVER (PARTITION BY opportunity_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_cases (
  CONSTRAINT case_pk_not_null EXPECT (case_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT case_status_valid EXPECT (status IN ('open', 'in_progress', 'resolved', 'closed')) ON VIOLATION DROP ROW
)
AS
SELECT
  case_id,
  account_id,
  contact_id,
  owner_employee_id,
  category,
  status,
  priority,
  CAST(created_at AS TIMESTAMP) AS created_at,
  CAST(resolved_at AS TIMESTAMP) AS resolved_at,
  _ingested_at
FROM bronze_cases
QUALIFY ROW_NUMBER() OVER (PARTITION BY case_id ORDER BY _ingested_at DESC) = 1;
