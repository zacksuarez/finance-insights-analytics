CREATE OR REPLACE VIEW dq_v2_results AS
SELECT 'executive_kpi_period_unique' AS check_name,
       count(*) - count(DISTINCT period) AS failure_count
FROM mart_executive_kpis
UNION ALL
SELECT 'executive_kpi_revenue_reconciles', count(*)
FROM mart_executive_kpis k
JOIN mart_monthly_pnl p USING (period)
WHERE abs(k.revenue - p.revenue) > 0.01
UNION ALL
SELECT 'executive_kpi_gross_margin_valid', count(*)
FROM mart_executive_kpis
WHERE abs(gross_margin_pct - gross_profit / nullif(revenue, 0)) > 0.000001
UNION ALL
SELECT 'customer_profitability_grain_unique', count(*)
FROM (
    SELECT year, customer_id FROM mart_customer_profitability_v2
    GROUP BY year, customer_id HAVING count(*) > 1
) duplicates
UNION ALL
SELECT 'customer_revenue_reconciles', count(*)
FROM (
    WITH customer AS (
        SELECT year, sum(revenue) AS customer_revenue
        FROM mart_customer_profitability_v2
        GROUP BY year
    ), executive AS (
        SELECT year, sum(revenue) AS executive_revenue
        FROM mart_executive_kpis
        GROUP BY year
    )
    SELECT customer.year, customer_revenue, executive_revenue
    FROM customer JOIN executive USING (year)
) totals
WHERE abs(customer_revenue - executive_revenue) > 0.01
UNION ALL
SELECT 'concentration_metrics_valid', count(*)
FROM mart_customer_concentration_v2
WHERE top_1_revenue_pct < 0
   OR top_1_revenue_pct > top_5_revenue_pct
   OR top_5_revenue_pct > top_10_revenue_pct
   OR top_10_revenue_pct > 1
   OR hhi < 0 OR hhi > 10000
UNION ALL
SELECT 'forecast_accuracy_metrics_valid', count(*)
FROM mart_forecast_accuracy_v2
WHERE forecast_accuracy_pct < 0 OR forecast_accuracy_pct > 1
   OR absolute_forecast_error < 0
   OR absolute_forecast_error_pct < 0
UNION ALL
SELECT 'pipeline_coverage_calculation_valid', count(*)
FROM mart_pipeline_analysis_v2
WHERE abs(weighted_pipeline_coverage - regional_weighted_pipeline / nullif(revenue_requirement, 0)) > 0.000001
UNION ALL
SELECT 'structural_opex_rule_surfaces_known_pattern',
       CASE WHEN count(*) > 0 THEN 0 ELSE 1 END
FROM mart_opex_management_v2
WHERE department_name = 'Engineering'
  AND account_name = 'Software'
  AND variance_classification = 'Structural Overrun'
UNION ALL
SELECT 'regional_revenue_reconciles', count(*)
FROM (
    SELECT r.period, sum(r.revenue) AS regional_revenue, k.revenue AS executive_revenue
    FROM mart_regional_performance_v2 r
    JOIN mart_executive_kpis k USING (period)
    GROUP BY r.period, k.revenue
) totals
WHERE abs(regional_revenue - executive_revenue) > 0.01
UNION ALL
SELECT 'scenario_calculations_valid', count(*)
FROM mart_scenario_analysis
WHERE abs(scenario_gross_profit - scenario_revenue * scenario_gross_margin_pct) > 0.01
   OR abs(scenario_operating_contribution - (scenario_gross_profit + scenario_operating_expense)) > 0.01
UNION ALL
SELECT 'scenario_names_complete',
       CASE WHEN count(DISTINCT scenario_name) = 3
              AND min(scenario_name IN ('Base', 'Upside', 'Downside'))
            THEN 0 ELSE 1 END
FROM mart_scenario_analysis
UNION ALL
SELECT 'issue_register_id_unique', count(*) - count(DISTINCT issue_id)
FROM mart_management_issue_register
UNION ALL
SELECT 'issue_register_valid_periods', count(*)
FROM mart_management_issue_register i
LEFT JOIN dim_date d USING (period)
WHERE d.date_key IS NULL
UNION ALL
SELECT 'issue_register_valid_regions', count(*)
FROM mart_management_issue_register i
LEFT JOIN (SELECT DISTINCT region FROM dim_customer) r ON i.entity_name = r.region
WHERE i.entity_type = 'Region' AND r.region IS NULL
UNION ALL
SELECT 'issue_register_valid_customers', count(*)
FROM mart_management_issue_register i
LEFT JOIN dim_customer c ON i.entity_name = c.customer_name
WHERE i.entity_type = 'Customer' AND c.customer_key IS NULL
UNION ALL
SELECT 'issue_register_valid_opex_entities', count(*)
FROM mart_management_issue_register i
LEFT JOIN mart_opex_management_v2 o
  ON i.period = o.period
 AND i.entity_name = o.department_name || ' / ' || o.account_name
WHERE i.entity_type = 'Department / Account' AND o.period IS NULL
UNION ALL
SELECT 'v2_marts_nonempty',
       CASE WHEN
           (SELECT count(*) FROM mart_executive_kpis) > 0
       AND (SELECT count(*) FROM mart_customer_profitability_v2) > 0
       AND (SELECT count(*) FROM mart_customer_concentration_v2) > 0
       AND (SELECT count(*) FROM mart_margin_analysis) > 0
       AND (SELECT count(*) FROM mart_forecast_accuracy_v2) > 0
       AND (SELECT count(*) FROM mart_pipeline_analysis_v2) > 0
       AND (SELECT count(*) FROM mart_opex_management_v2) > 0
       AND (SELECT count(*) FROM mart_regional_performance_v2) > 0
       AND (SELECT count(*) FROM mart_management_issue_register) > 0
       THEN 0 ELSE 1 END;
