-- DQ dashboard views. Also created automatically by create_data_quality_monitors.py (same logic, parameterized by --output-schema).
-- Run this file manually only if you need to recreate views without running the DQ job.
CREATE OR REPLACE VIEW bx4.butterfly.dq_rule_results AS
WITH checks AS (
  SELECT
    'silver_account' AS table_name,
    'null_account_id' AS rule_name,
    SUM(CASE WHEN account_id IS NULL THEN 1 ELSE 0 END) AS failed_records,
    COUNT(*) AS total_records
  FROM bx4.butterfly.silver_account

  UNION ALL
  SELECT
    'silver_contact' AS table_name,
    'null_email' AS rule_name,
    SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END) AS failed_records,
    COUNT(*) AS total_records
  FROM bx4.butterfly.silver_contact

  UNION ALL
  SELECT
    'silver_transactions' AS table_name,
    'negative_net_sales' AS rule_name,
    SUM(CASE WHEN net_sales < 0 THEN 1 ELSE 0 END) AS failed_records,
    COUNT(*) AS total_records
  FROM bx4.butterfly.silver_transactions

  UNION ALL
  SELECT
    'gold_customer_360' AS table_name,
    'null_region' AS rule_name,
    SUM(CASE WHEN region IS NULL THEN 1 ELSE 0 END) AS failed_records,
    COUNT(*) AS total_records
  FROM bx4.butterfly.gold_customer_360

  UNION ALL
  SELECT
    'gold_customer_360' AS table_name,
    'negative_open_pipeline' AS rule_name,
    SUM(CASE WHEN open_pipeline_amount < 0 THEN 1 ELSE 0 END) AS failed_records,
    COUNT(*) AS total_records
  FROM bx4.butterfly.gold_customer_360
)
SELECT
  table_name,
  rule_name,
  failed_records,
  total_records,
  CASE WHEN total_records = 0 THEN 0 ELSE failed_records / total_records END AS failure_ratio,
  current_timestamp() AS measured_at
FROM checks;

CREATE OR REPLACE VIEW bx4.butterfly.dq_monitor_assets AS
SELECT
  table_name,
  object_id,
  refresh_id,
  metric_tables,
  monitor_json,
  from_unixtime(updated_at) AS updated_at
FROM bx4.butterfly.dq_monitor_registry;

CREATE OR REPLACE VIEW bx4.butterfly.dq_summary AS
SELECT
  table_name,
  COUNT(*) AS rules_count,
  SUM(failed_records) AS failed_records,
  SUM(total_records) AS total_records,
  AVG(1 - failure_ratio) AS avg_pass_rate,
  MAX(measured_at) AS measured_at
FROM bx4.butterfly.dq_rule_results
GROUP BY table_name;
