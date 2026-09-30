CREATE OR REPLACE VIEW dq_results AS
SELECT 'actual_source_fact_row_count' AS check_name,
       abs((SELECT count(*) FROM stg_erp_transactions) - (SELECT count(*) FROM fact_actuals)) AS failure_count
UNION ALL
SELECT 'plan_source_fact_row_count',
       abs((SELECT count(*) FROM stg_epm_plan) - (SELECT count(*) FROM fact_plan))
UNION ALL
SELECT 'pipeline_source_fact_row_count',
       abs((SELECT count(*) FROM stg_sales_pipeline) - (SELECT count(*) FROM fact_pipeline))
UNION ALL
SELECT 'operational_source_fact_row_count',
       abs((SELECT count(*) FROM stg_operational_kpis) - (SELECT count(*) FROM fact_operational_kpi))
UNION ALL
SELECT 'actual_transaction_pk_unique',
       count(*) - count(DISTINCT transaction_id) AS failure_count
FROM fact_actuals
UNION ALL
SELECT 'pipeline_opportunity_pk_unique', count(*) - count(DISTINCT opportunity_id)
FROM fact_pipeline
UNION ALL
SELECT 'customer_dimension_pk_unique', count(*) - count(DISTINCT customer_key)
FROM dim_customer
UNION ALL
SELECT 'plan_natural_grain_unique', count(*)
FROM (
    SELECT date_key, account_key, department_key, customer_key, product_key, scenario_version
    FROM fact_plan
    GROUP BY ALL
    HAVING count(*) > 1
) duplicates
UNION ALL
SELECT 'operational_kpi_natural_grain_unique', count(*)
FROM (
    SELECT date_key, record_type, customer_key, department_key
    FROM fact_operational_kpi
    GROUP BY ALL
    HAVING count(*) > 1
) duplicates
UNION ALL
SELECT 'actual_required_dimensions', count(*)
FROM fact_actuals
WHERE date_key IS NULL OR account_key IS NULL OR department_key IS NULL OR amount IS NULL
UNION ALL
SELECT 'actual_customer_fk', count(*)
FROM fact_actuals f
LEFT JOIN dim_customer c USING (customer_key)
WHERE f.customer_key IS NOT NULL AND c.customer_key IS NULL
UNION ALL
SELECT 'actual_product_fk', count(*)
FROM fact_actuals f
LEFT JOIN dim_product p USING (product_key)
WHERE f.product_key IS NOT NULL AND p.product_key IS NULL
UNION ALL
SELECT 'plan_required_dimensions', count(*)
FROM fact_plan
WHERE date_key IS NULL OR account_key IS NULL OR department_key IS NULL OR plan_amount IS NULL
UNION ALL
SELECT 'plan_customer_fk', count(*)
FROM fact_plan f
LEFT JOIN dim_customer c USING (customer_key)
WHERE f.customer_key IS NOT NULL AND c.customer_key IS NULL
UNION ALL
SELECT 'plan_product_fk', count(*)
FROM fact_plan f
LEFT JOIN dim_product p USING (product_key)
WHERE f.product_key IS NOT NULL AND p.product_key IS NULL
UNION ALL
SELECT 'pipeline_required_dimensions', count(*)
FROM fact_pipeline
WHERE created_date_key IS NULL OR expected_close_date_key IS NULL
   OR customer_key IS NULL OR product_key IS NULL
UNION ALL
SELECT 'pipeline_customer_fk', count(*)
FROM fact_pipeline f
LEFT JOIN dim_customer c USING (customer_key)
WHERE c.customer_key IS NULL
UNION ALL
SELECT 'pipeline_product_fk', count(*)
FROM fact_pipeline f
LEFT JOIN dim_product p USING (product_key)
WHERE p.product_key IS NULL
UNION ALL
SELECT 'operational_required_dimensions', count(*)
FROM fact_operational_kpi
WHERE date_key IS NULL
   OR (record_type = 'Customer' AND customer_key IS NULL)
   OR (record_type = 'Department' AND department_key IS NULL)
UNION ALL
SELECT 'plan_versions_valid', count(*)
FROM fact_plan
WHERE scenario_version NOT IN ('Budget', 'Forecast')
UNION ALL
SELECT 'pipeline_probability_valid', count(*)
FROM fact_pipeline
WHERE probability < 0 OR probability > 1 OR pipeline_amount < 0
UNION ALL
SELECT 'operational_kpis_nonnegative', count(*)
FROM fact_operational_kpi
WHERE coalesce(active_users, 0) < 0
   OR coalesce(support_tickets, 0) < 0
   OR coalesce(implementation_hours, 0) < 0
   OR coalesce(usage_metric, 0) < 0
   OR coalesce(headcount, 0) < 0
UNION ALL
SELECT 'actual_source_fact_reconciliation', count(*)
FROM mart_reconciliation
WHERE measure = 'Actuals' AND abs(source_total - fact_total) > 0.01
UNION ALL
SELECT 'actual_fact_mart_reconciliation', count(*)
FROM mart_reconciliation
WHERE measure = 'Actuals' AND abs(fact_total - mart_total) > 0.01
UNION ALL
SELECT 'plan_reconciliation', count(*)
FROM mart_reconciliation
WHERE measure IN ('Budget', 'Forecast')
  AND (abs(source_total - fact_total) > 0.01 OR abs(fact_total - mart_total) > 0.01);
