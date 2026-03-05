CREATE OR REPLACE VIEW bx4.butterfly.gold_customer_kpis_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
comment: "Governed KPI metric view built from daily customer KPI rollups"
source: bx4.butterfly.gold_customer_kpis_daily

dimensions:
  - name: Metric Date
    expr: metric_date
    comment: "Daily KPI snapshot date"
  - name: Metric Month
    expr: DATE_TRUNC('MONTH', metric_date)
    comment: "Month bucket for trend analysis"

measures:
  - name: Customer Count
    expr: SUM(customer_count)
    comment: "Total customers in KPI snapshots"
  - name: Total Net Sales
    expr: SUM(total_net_sales)
    comment: "Sum of net sales"
  - name: Total Open Pipeline
    expr: SUM(total_open_pipeline)
    comment: "Sum of open pipeline"
  - name: Engaged Customers
    expr: SUM(engaged_customers)
    comment: "Customers with activity"
  - name: Avg Resolution Hours
    expr: AVG(avg_resolution_hours)
    comment: "Average support case resolution hours"
  - name: Engagement Rate
    expr: CASE WHEN SUM(customer_count) = 0 THEN 0 ELSE SUM(engaged_customers) / SUM(customer_count) END
    comment: "Engaged customers divided by total customers"
$$;
