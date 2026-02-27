-- Customer 360 dashboard datasets (with product company/brand filters)
SELECT
  account_id,
  account_name,
  region,
  segment,
  tier,
  primary_product_company,
  primary_product_brand,
  lifetime_net_sales,
  open_pipeline_amount
FROM bx4.butterfly.gold_customer_360
LIMIT 100;

SELECT
  product_company,
  product_brand,
  customer_count,
  order_lines,
  net_sales,
  gross_profit
FROM bx4.butterfly.gold_product_company_brand_performance
LIMIT 100;

SELECT
  DATE_TRUNC('MONTH', invoice_date) AS sales_month,
  SUM(net_sales) AS monthly_net_sales,
  SUM(gross_profit) AS monthly_gross_profit
FROM bx4.butterfly.silver_transactions
GROUP BY DATE_TRUNC('MONTH', invoice_date)
LIMIT 100;

SELECT
  stage_name,
  SUM(amount) AS pipeline_amount,
  COUNT(*) AS opportunities
FROM bx4.butterfly.silver_opportunities
GROUP BY stage_name
LIMIT 100;

SELECT
  c.region,
  p.product_company,
  SUM(t.net_sales) AS net_sales
FROM bx4.butterfly.silver_transactions t
INNER JOIN bx4.butterfly.silver_account c ON c.account_id = t.account_id
INNER JOIN bx4.butterfly.silver_product p ON p.product_id = t.product_id
GROUP BY c.region, p.product_company
LIMIT 100;

SELECT activity_date, activity_type, activity_count, successful_count
FROM bx4.butterfly.gold_activity_trend_30d
LIMIT 100;

SELECT COUNT(*) AS customer_count, SUM(lifetime_net_sales) AS total_net_sales, SUM(open_pipeline_amount) AS total_open_pipeline
FROM bx4.butterfly.gold_customer_360;

-- Data Quality dashboard datasets
SELECT SUM(rules_count) AS rules_count, SUM(failed_records) AS failed_records, SUM(total_records) AS total_records, AVG(avg_pass_rate) AS avg_pass_rate
FROM bx4.butterfly.dq_summary;

SELECT table_name, rules_count, failed_records, total_records, avg_pass_rate, measured_at
FROM bx4.butterfly.dq_summary
LIMIT 100;

SELECT table_name, rule_name, failed_records, total_records, failure_ratio, measured_at
FROM bx4.butterfly.dq_rule_results
LIMIT 200;

SELECT table_name, object_id, refresh_id, metric_tables, updated_at
FROM bx4.butterfly.dq_monitor_assets
LIMIT 100;
