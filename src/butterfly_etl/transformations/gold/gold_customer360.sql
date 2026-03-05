CREATE OR REFRESH MATERIALIZED VIEW gold_customer_360 (
  CONSTRAINT customer360_account_id_not_null EXPECT (account_id IS NOT NULL) ON VIOLATION DROP ROW
)
AS
WITH transaction_rollup AS (
  SELECT
    account_id,
    COUNT(*) AS lifetime_orders,
    SUM(net_sales) AS lifetime_net_sales,
    SUM(gross_profit) AS lifetime_gross_profit,
    MAX(invoice_date) AS last_invoice_date
  FROM silver_transactions
  GROUP BY account_id
),
product_ranked AS (
  SELECT
    t.account_id,
    p.product_company,
    p.product_brand,
    SUM(t.net_sales) AS brand_net_sales,
    ROW_NUMBER() OVER (
      PARTITION BY t.account_id
      ORDER BY SUM(t.net_sales) DESC, p.product_company, p.product_brand
    ) AS rn
  FROM silver_transactions t
  INNER JOIN silver_product p ON p.product_id = t.product_id
  GROUP BY t.account_id, p.product_company, p.product_brand
),
primary_product AS (
  SELECT
    account_id,
    product_company AS primary_product_company,
    product_brand AS primary_product_brand
  FROM product_ranked
  WHERE rn = 1
),
activity_rollup AS (
  SELECT
    account_id,
    COUNT(*) AS activities_180d,
    SUM(CASE WHEN is_successful THEN 1 ELSE 0 END) AS successful_activities_180d,
    MAX(activity_date) AS last_activity_date
  FROM silver_activities
  WHERE activity_date >= date_sub(current_date(), 180)
  GROUP BY account_id
),
opportunity_rollup AS (
  SELECT
    account_id,
    SUM(CASE WHEN stage_name = 'closed_won' THEN amount ELSE 0 END) AS won_amount,
    SUM(CASE WHEN stage_name NOT IN ('closed_won', 'closed_lost') THEN amount ELSE 0 END) AS open_pipeline_amount,
    MAX(close_date) AS next_expected_close_date
  FROM silver_opportunities
  GROUP BY account_id
),
case_rollup AS (
  SELECT
    account_id,
    COUNT(*) AS support_cases_180d,
    SUM(CASE WHEN status IN ('resolved', 'closed') THEN 1 ELSE 0 END) AS resolved_cases_180d,
    AVG(
      CASE
        WHEN resolved_at IS NOT NULL THEN (unix_timestamp(resolved_at) - unix_timestamp(created_at)) / 3600.0
        ELSE NULL
      END
    ) AS avg_resolution_hours_180d
  FROM silver_cases
  WHERE CAST(created_at AS DATE) >= date_sub(current_date(), 180)
  GROUP BY account_id
),
contact_rollup AS (
  SELECT
    account_id,
    COUNT(*) AS contact_count
  FROM silver_contact
  GROUP BY account_id
)
SELECT
  a.account_id,
  a.account_name,
  a.region,
  a.segment,
  a.tier,
  a.created_date,
  coalesce(c.contact_count, 0) AS contact_count,
  coalesce(t.lifetime_orders, 0) AS lifetime_orders,
  coalesce(t.lifetime_net_sales, 0.0) AS lifetime_net_sales,
  coalesce(t.lifetime_gross_profit, 0.0) AS lifetime_gross_profit,
  coalesce(pp.primary_product_company, 'Unknown') AS primary_product_company,
  coalesce(pp.primary_product_brand, 'Unknown') AS primary_product_brand,
  t.last_invoice_date,
  coalesce(ar.activities_180d, 0) AS activities_180d,
  coalesce(ar.successful_activities_180d, 0) AS successful_activities_180d,
  ar.last_activity_date,
  bx4.butterfly.mask_won_amount_for_robert(coalesce(orx.won_amount, 0.0)) AS won_amount,
  coalesce(orx.open_pipeline_amount, 0.0) AS open_pipeline_amount,
  orx.next_expected_close_date,
  coalesce(cr.support_cases_180d, 0) AS support_cases_180d,
  coalesce(cr.resolved_cases_180d, 0) AS resolved_cases_180d,
  coalesce(cr.avg_resolution_hours_180d, 0.0) AS avg_resolution_hours_180d,
  current_timestamp() AS _updated_at
FROM silver_account a
LEFT JOIN transaction_rollup t ON t.account_id = a.account_id
LEFT JOIN activity_rollup ar ON ar.account_id = a.account_id
LEFT JOIN opportunity_rollup orx ON orx.account_id = a.account_id
LEFT JOIN case_rollup cr ON cr.account_id = a.account_id
LEFT JOIN contact_rollup c ON c.account_id = a.account_id
LEFT JOIN primary_product pp ON pp.account_id = a.account_id;

CREATE OR REFRESH MATERIALIZED VIEW gold_customer_kpis_daily
AS
SELECT
  current_date() AS metric_date,
  COUNT(*) AS customer_count,
  SUM(lifetime_net_sales) AS total_net_sales,
  SUM(open_pipeline_amount) AS total_open_pipeline,
  AVG(avg_resolution_hours_180d) AS avg_resolution_hours,
  SUM(CASE WHEN activities_180d > 0 THEN 1 ELSE 0 END) AS engaged_customers
FROM gold_customer_360;

CREATE OR REFRESH MATERIALIZED VIEW gold_region_performance
AS
SELECT
  region,
  COUNT(*) AS customer_count,
  SUM(lifetime_net_sales) AS net_sales,
  SUM(open_pipeline_amount) AS open_pipeline,
  AVG(avg_resolution_hours_180d) AS avg_resolution_hours,
  SUM(support_cases_180d) AS support_cases_180d
FROM gold_customer_360
GROUP BY region;

CREATE OR REFRESH MATERIALIZED VIEW gold_product_company_brand_performance
AS
SELECT
  p.product_company,
  p.product_brand,
  COUNT(DISTINCT t.account_id) AS customer_count,
  COUNT(*) AS order_lines,
  SUM(t.net_sales) AS net_sales,
  SUM(t.gross_profit) AS gross_profit
FROM silver_transactions t
INNER JOIN silver_product p ON p.product_id = t.product_id
GROUP BY p.product_company, p.product_brand;

CREATE OR REFRESH MATERIALIZED VIEW gold_activity_trend_30d
AS
SELECT
  activity_date,
  activity_type,
  COUNT(*) AS activity_count,
  SUM(CASE WHEN is_successful THEN 1 ELSE 0 END) AS successful_count
FROM silver_activities
WHERE activity_date >= date_sub(current_date(), 30)
GROUP BY activity_date, activity_type;
