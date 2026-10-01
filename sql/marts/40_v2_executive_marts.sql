CREATE OR REPLACE TABLE mart_executive_kpis AS
WITH plan_totals AS (
    SELECT
        d.period,
        sum(f.budget_amount) AS budget_operating_contribution,
        sum(f.forecast_amount) AS forecast_operating_contribution,
        sum(CASE WHEN a.account_category = 'Revenue' THEN f.forecast_amount ELSE 0 END) AS forecast_revenue
    FROM mart_finance_monthly f
    JOIN dim_date d USING (date_key)
    JOIN dim_account a USING (account_key)
    GROUP BY d.period
), customer_rank AS (
    SELECT
        period,
        customer_id,
        revenue,
        row_number() OVER (PARTITION BY period ORDER BY revenue DESC) AS revenue_rank,
        revenue / nullif(sum(revenue) OVER (PARTITION BY period), 0) AS revenue_share
    FROM mart_customer_profitability
), customer_metrics AS (
    SELECT
        period,
        count(*) AS customer_count,
        sum(CASE WHEN revenue_rank <= 10 THEN revenue_share ELSE 0 END) AS top_10_customer_revenue_pct
    FROM customer_rank
    GROUP BY period
), pipeline AS (
    SELECT period, sum(gross_pipeline) AS pipeline_amount, sum(weighted_pipeline) AS weighted_pipeline
    FROM mart_pipeline_coverage
    GROUP BY period
), base AS (
    SELECT
        p.period,
        p.year,
        p.revenue,
        lag(p.revenue, 12) OVER (ORDER BY p.period) AS revenue_prior_year,
        pt.budget_operating_contribution,
        pt.forecast_operating_contribution,
        pt.forecast_revenue,
        p.cogs,
        p.gross_profit,
        p.gross_margin_pct,
        lag(p.gross_margin_pct, 12) OVER (ORDER BY p.period) AS gross_margin_prior_year_pct,
        p.operating_expense,
        p.operating_contribution,
        cm.customer_count,
        cm.top_10_customer_revenue_pct,
        pl.pipeline_amount,
        pl.weighted_pipeline
    FROM mart_monthly_pnl p
    JOIN plan_totals pt USING (period)
    JOIN customer_metrics cm USING (period)
    JOIN pipeline pl USING (period)
)
SELECT
    period,
    year,
    revenue,
    CASE WHEN revenue_prior_year = 0 THEN NULL ELSE revenue / revenue_prior_year - 1 END AS revenue_yoy_pct,
    operating_contribution - budget_operating_contribution AS budget_variance,
    CASE WHEN budget_operating_contribution = 0 THEN NULL
         ELSE (operating_contribution - budget_operating_contribution) / abs(budget_operating_contribution) END AS budget_variance_pct,
    operating_contribution - forecast_operating_contribution AS forecast_variance,
    CASE WHEN forecast_operating_contribution = 0 THEN NULL
         ELSE (operating_contribution - forecast_operating_contribution) / abs(forecast_operating_contribution) END AS forecast_variance_pct,
    cogs,
    gross_profit,
    gross_margin_pct,
    (gross_margin_pct - gross_margin_prior_year_pct) * 10000 AS gross_margin_yoy_bps,
    operating_expense,
    operating_contribution,
    CASE WHEN revenue = 0 THEN NULL ELSE operating_contribution / revenue END AS operating_contribution_margin_pct,
    customer_count,
    top_10_customer_revenue_pct,
    CASE WHEN forecast_revenue = 0 THEN NULL
         ELSE greatest(0, 1 - abs(revenue - forecast_revenue) / abs(forecast_revenue)) END AS forecast_accuracy_pct,
    pipeline_amount,
    weighted_pipeline,
    CASE WHEN forecast_revenue = 0 THEN NULL ELSE weighted_pipeline / forecast_revenue END AS pipeline_coverage
FROM base;

CREATE OR REPLACE TABLE mart_customer_profitability_v2 AS
WITH annual AS (
    SELECT
        year,
        customer_id,
        customer_name,
        segment,
        region,
        sum(revenue) AS revenue,
        sum(cogs) AS cogs,
        sum(gross_profit) AS gross_profit,
        sum(gross_profit) / nullif(sum(revenue), 0) AS gross_margin_pct,
        sum(support_tickets) AS support_tickets,
        sum(implementation_hours) AS implementation_hours
    FROM mart_customer_profitability
    GROUP BY year, customer_id, customer_name, segment, region
), compared AS (
    SELECT
        *,
        lag(revenue) OVER (PARTITION BY customer_id ORDER BY year) AS prior_year_revenue,
        lag(gross_profit) OVER (PARTITION BY customer_id ORDER BY year) AS prior_year_gross_profit,
        lag(gross_margin_pct) OVER (PARTITION BY customer_id ORDER BY year) AS prior_year_gross_margin_pct,
        revenue / nullif(sum(revenue) OVER (PARTITION BY year), 0) AS revenue_concentration_pct,
        dense_rank() OVER (PARTITION BY year ORDER BY revenue DESC) AS revenue_rank,
        dense_rank() OVER (PARTITION BY year ORDER BY gross_profit DESC) AS gross_profit_rank,
        count(*) OVER (PARTITION BY year) AS customer_count,
        sum(gross_profit) OVER (PARTITION BY year) / nullif(sum(revenue) OVER (PARTITION BY year), 0) AS company_gross_margin_pct
    FROM annual
), metrics AS (
    SELECT
        *,
        CASE WHEN prior_year_revenue = 0 THEN NULL ELSE revenue / prior_year_revenue - 1 END AS revenue_growth_pct,
        CASE WHEN prior_year_gross_profit = 0 THEN NULL ELSE gross_profit / prior_year_gross_profit - 1 END AS gross_profit_growth_pct,
        (gross_margin_pct - prior_year_gross_margin_pct) * 10000 AS margin_change_bps
    FROM compared
)
SELECT
    *,
    CASE
        WHEN margin_change_bps > 100 THEN 'Improving'
        WHEN margin_change_bps < -100 THEN 'Deteriorating'
        ELSE 'Stable'
    END AS profitability_trend,
    CASE
        WHEN revenue_rank <= greatest(10, ceil(customer_count * 0.25)) AND gross_margin_pct >= company_gross_margin_pct THEN 'High Revenue / High Margin'
        WHEN revenue_rank <= greatest(10, ceil(customer_count * 0.25))
             AND margin_change_bps <= -(SELECT threshold_value FROM config_management_thresholds WHERE threshold_name = 'customer_margin_deterioration_bps')
             THEN 'High Revenue / Deteriorating Margin'
        WHEN gross_profit_growth_pct > 0 AND margin_change_bps > 100 THEN 'Improving Profitability'
        WHEN revenue_growth_pct < (SELECT threshold_value FROM config_management_thresholds WHERE threshold_name = 'customer_low_growth_pct')
             AND gross_margin_pct < company_gross_margin_pct THEN 'Low Growth / Low Margin'
        ELSE 'Core / Monitor'
    END AS profitability_segment
FROM metrics;

CREATE OR REPLACE TABLE mart_customer_concentration_v2 AS
WITH ranked AS (
    SELECT
        period,
        customer_id,
        revenue,
        row_number() OVER (PARTITION BY period ORDER BY revenue DESC) AS revenue_rank,
        revenue / nullif(sum(revenue) OVER (PARTITION BY period), 0) AS revenue_share
    FROM mart_customer_profitability
), monthly AS (
    SELECT
        period,
        max(CASE WHEN revenue_rank = 1 THEN revenue_share END) AS top_1_revenue_pct,
        sum(CASE WHEN revenue_rank <= 5 THEN revenue_share ELSE 0 END) AS top_5_revenue_pct,
        sum(CASE WHEN revenue_rank <= 10 THEN revenue_share ELSE 0 END) AS top_10_revenue_pct,
        sum(revenue_share * revenue_share) * 10000 AS hhi,
        count(*) AS customer_count
    FROM ranked
    GROUP BY period
)
SELECT
    *,
    top_10_revenue_pct - lag(top_10_revenue_pct, 12) OVER (ORDER BY period) AS top_10_yoy_change,
    hhi - lag(hhi, 12) OVER (ORDER BY period) AS hhi_yoy_change
FROM monthly;

CREATE OR REPLACE TABLE mart_margin_analysis AS
WITH product_components AS (
    SELECT
        d.year,
        'Product' AS dimension_type,
        p.product_name AS member_name,
        sum(CASE WHEN a.account_category = 'Revenue' THEN f.amount ELSE 0 END) AS revenue,
        sum(CASE WHEN a.account_category IN ('Revenue', 'COGS') THEN f.amount ELSE 0 END) AS gross_profit
    FROM fact_actuals f
    JOIN dim_date d USING (date_key)
    JOIN dim_account a USING (account_key)
    JOIN dim_product p USING (product_key)
    GROUP BY d.year, p.product_name
), region_components AS (
    SELECT year, 'Region' AS dimension_type, region AS member_name,
           sum(revenue) AS revenue, sum(gross_profit) AS gross_profit
    FROM mart_customer_profitability
    GROUP BY year, region
), segment_components AS (
    SELECT year, 'Customer Segment' AS dimension_type, segment AS member_name,
           sum(revenue) AS revenue, sum(gross_profit) AS gross_profit
    FROM mart_customer_profitability
    GROUP BY year, segment
), components AS (
    SELECT * FROM product_components
    UNION ALL SELECT * FROM region_components
    UNION ALL SELECT * FROM segment_components
), metrics AS (
    SELECT
        *,
        gross_profit / nullif(revenue, 0) AS gross_margin_pct,
        revenue / nullif(sum(revenue) OVER (PARTITION BY year, dimension_type), 0) AS revenue_mix_pct
    FROM components
), compared AS (
    SELECT
        *,
        lag(gross_margin_pct) OVER (PARTITION BY dimension_type, member_name ORDER BY year) AS prior_year_gross_margin_pct,
        lag(revenue_mix_pct) OVER (PARTITION BY dimension_type, member_name ORDER BY year) AS prior_year_revenue_mix_pct
    FROM metrics
)
SELECT
    *,
    (gross_margin_pct - prior_year_gross_margin_pct) * 10000 AS gross_margin_change_bps,
    revenue_mix_pct - prior_year_revenue_mix_pct AS revenue_mix_change_pct,
    (revenue_mix_pct - prior_year_revenue_mix_pct) * prior_year_gross_margin_pct * 10000 AS mix_effect_bps,
    revenue_mix_pct * (gross_margin_pct - prior_year_gross_margin_pct) * 10000 AS margin_rate_effect_bps
FROM compared;

CREATE OR REPLACE TABLE mart_forecast_accuracy_v2 AS
WITH company AS (
    SELECT
        d.period,
        'Company' AS entity_type,
        'Company Total' AS entity_name,
        sum(f.actual_amount) AS actual_amount,
        sum(f.forecast_amount) AS forecast_amount
    FROM mart_finance_monthly f
    JOIN dim_date d USING (date_key)
    JOIN dim_account a USING (account_key)
    WHERE a.account_category = 'Revenue'
    GROUP BY d.period
), region AS (
    SELECT period, 'Region' AS entity_type, region AS entity_name,
           actual_revenue AS actual_amount, forecast_revenue AS forecast_amount
    FROM mart_regional_performance
), department_account AS (
    SELECT period, 'Department / Account' AS entity_type,
           department_name || ' / ' || account_name AS entity_name,
           actual_amount, forecast_amount
    FROM mart_department_opex
), combined AS (
    SELECT * FROM company
    UNION ALL SELECT * FROM region
    UNION ALL SELECT * FROM department_account
), errors AS (
    SELECT
        *,
        actual_amount - forecast_amount AS forecast_error,
        abs(actual_amount - forecast_amount) AS absolute_forecast_error,
        CASE WHEN forecast_amount = 0 THEN NULL ELSE abs(actual_amount - forecast_amount) / abs(forecast_amount) END AS absolute_forecast_error_pct,
        CASE WHEN forecast_amount = 0 THEN NULL ELSE (actual_amount - forecast_amount) / abs(forecast_amount) END AS bias_pct
    FROM combined
), accuracy AS (
    SELECT *, greatest(0, 1 - absolute_forecast_error_pct) AS forecast_accuracy_pct
    FROM errors
)
SELECT
    *,
    avg(absolute_forecast_error_pct) OVER (
        PARTITION BY entity_type, entity_name ORDER BY period ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS mape_3m,
    avg(absolute_forecast_error_pct) OVER (
        PARTITION BY entity_type, entity_name ORDER BY period ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
    ) AS mape_6m,
    avg(forecast_accuracy_pct) OVER (
        PARTITION BY entity_type, entity_name ORDER BY period ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS rolling_3m_accuracy_pct,
    avg(forecast_accuracy_pct) OVER (
        PARTITION BY entity_type, entity_name ORDER BY period ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
    ) AS rolling_6m_accuracy_pct
FROM accuracy;

CREATE OR REPLACE TABLE mart_pipeline_analysis_v2 AS
WITH stage_pipeline AS (
    SELECT
        d.period,
        p.region,
        p.stage,
        sum(p.pipeline_amount) AS gross_pipeline,
        sum(p.pipeline_amount * p.probability) AS weighted_pipeline
    FROM fact_pipeline p
    JOIN dim_date d ON p.expected_close_date_key = d.date_key
    GROUP BY d.period, p.region, p.stage
), enriched AS (
    SELECT
        sp.*,
        sum(sp.gross_pipeline) OVER (PARTITION BY sp.period, sp.region) AS regional_gross_pipeline,
        sum(sp.weighted_pipeline) OVER (PARTITION BY sp.period, sp.region) AS regional_weighted_pipeline,
        sp.gross_pipeline / nullif(sum(sp.gross_pipeline) OVER (PARTITION BY sp.period, sp.region), 0) AS stage_mix_pct,
        rp.forecast_revenue AS revenue_requirement
    FROM stage_pipeline sp
    JOIN mart_regional_performance rp USING (period, region)
)
SELECT
    *,
    regional_weighted_pipeline / nullif(revenue_requirement, 0) AS weighted_pipeline_coverage,
    gross_pipeline / nullif(lag(gross_pipeline, 1) OVER (PARTITION BY region, stage ORDER BY period), 0) - 1 AS gross_pipeline_growth_pct,
    weighted_pipeline / nullif(lag(weighted_pipeline, 1) OVER (PARTITION BY region, stage ORDER BY period), 0) - 1 AS weighted_pipeline_growth_pct
FROM enriched;

CREATE OR REPLACE TABLE mart_opex_management_v2 AS
WITH base AS (
    SELECT
        *,
        actual_amount - budget_amount AS budget_variance,
        CASE WHEN budget_amount = 0 THEN NULL ELSE (actual_amount - budget_amount) / abs(budget_amount) END AS budget_variance_pct,
        CASE
            WHEN forecast_variance < 0
             AND (abs(forecast_variance) >= (SELECT threshold_value FROM config_management_thresholds WHERE threshold_name = 'opex_variance_material_amount')
               OR abs(forecast_variance_pct) >= (SELECT threshold_value FROM config_management_thresholds WHERE threshold_name = 'opex_variance_material_pct'))
            THEN 1 ELSE 0
        END AS material_unfavorable_flag
    FROM mart_department_opex
), windows AS (
    SELECT
        *,
        sum(forecast_variance) OVER (
            PARTITION BY department_name, account_name ORDER BY period ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3m_forecast_variance,
        sum(forecast_variance) OVER (
            PARTITION BY department_name, account_name, left(period, 4) ORDER BY period ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS ytd_forecast_variance,
        sum(material_unfavorable_flag) OVER (
            PARTITION BY department_name, account_name ORDER BY period ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) AS material_unfavorable_months_trailing_6
    FROM base
)
SELECT
    *,
    CASE
        WHEN material_unfavorable_flag = 1
         AND material_unfavorable_months_trailing_6 >= (SELECT threshold_value FROM config_management_thresholds WHERE threshold_name = 'opex_persistence_months')
        THEN 'Structural Overrun'
        WHEN material_unfavorable_flag = 1 THEN 'Potential Timing Issue'
        ELSE 'Within Tolerance'
    END AS variance_classification
FROM windows;

CREATE OR REPLACE TABLE mart_regional_performance_v2 AS
WITH financial AS (
    SELECT
        period,
        region,
        sum(revenue) AS revenue,
        sum(cogs) AS cogs,
        sum(gross_profit) AS gross_profit,
        sum(gross_profit) / nullif(sum(revenue), 0) AS gross_margin_pct,
        count(DISTINCT customer_id) AS customer_count
    FROM mart_customer_profitability
    GROUP BY period, region
), concentration AS (
    SELECT
        period,
        region,
        max(revenue_share) AS top_1_customer_revenue_pct
    FROM (
        SELECT period, region, customer_id,
               revenue / nullif(sum(revenue) OVER (PARTITION BY period, region), 0) AS revenue_share
        FROM mart_customer_profitability
    ) shares
    GROUP BY period, region
), pipeline AS (
    SELECT period, region, sum(gross_pipeline) AS gross_pipeline, sum(weighted_pipeline) AS weighted_pipeline
    FROM mart_pipeline_coverage
    GROUP BY period, region
), combined AS (
    SELECT
        f.*,
        rp.forecast_revenue,
        greatest(0, 1 - abs(f.revenue - rp.forecast_revenue) / nullif(abs(rp.forecast_revenue), 0)) AS forecast_accuracy_pct,
        p.gross_pipeline,
        p.weighted_pipeline,
        p.weighted_pipeline / nullif(rp.forecast_revenue, 0) AS pipeline_coverage,
        c.top_1_customer_revenue_pct
    FROM financial f
    JOIN mart_regional_performance rp USING (period, region)
    JOIN pipeline p USING (period, region)
    JOIN concentration c USING (period, region)
)
SELECT
    *,
    revenue / nullif(lag(revenue, 12) OVER (PARTITION BY region ORDER BY period), 0) - 1 AS revenue_yoy_pct,
    (gross_margin_pct - lag(gross_margin_pct, 12) OVER (PARTITION BY region ORDER BY period)) * 10000 AS gross_margin_yoy_bps,
    dense_rank() OVER (PARTITION BY period ORDER BY revenue DESC) AS revenue_rank,
    dense_rank() OVER (PARTITION BY period ORDER BY forecast_accuracy_pct DESC) AS forecast_accuracy_rank
FROM combined;

CREATE OR REPLACE TABLE mart_scenario_analysis AS
WITH baseline AS (
    SELECT
        max(year) AS baseline_year,
        sum(revenue) AS baseline_revenue,
        sum(gross_profit) AS baseline_gross_profit,
        sum(gross_profit) / nullif(sum(revenue), 0) AS baseline_gross_margin_pct,
        sum(operating_expense) AS baseline_operating_expense,
        sum(operating_contribution) AS baseline_operating_contribution
    FROM mart_monthly_pnl
    WHERE year = (SELECT max(year) FROM mart_monthly_pnl)
), projections AS (
    SELECT
        s.scenario_name,
        s.display_order,
        b.*,
        s.revenue_growth_adjustment,
        s.gross_margin_adjustment_bps,
        s.opex_growth_adjustment,
        b.baseline_revenue * (1 + s.revenue_growth_adjustment) AS scenario_revenue,
        b.baseline_gross_margin_pct + s.gross_margin_adjustment_bps / 10000 AS scenario_gross_margin_pct,
        b.baseline_operating_expense * (1 + s.opex_growth_adjustment) AS scenario_operating_expense
    FROM config_scenario_assumptions s
    CROSS JOIN baseline b
)
SELECT
    *,
    scenario_revenue * scenario_gross_margin_pct AS scenario_gross_profit,
    scenario_revenue * scenario_gross_margin_pct + scenario_operating_expense AS scenario_operating_contribution
FROM projections;

CREATE OR REPLACE TABLE mart_management_issue_register AS
WITH thresholds AS (
    SELECT
        max(CASE WHEN threshold_name = 'margin_deterioration_bps' THEN threshold_value END) AS margin_deterioration_bps,
        max(CASE WHEN threshold_name = 'forecast_accuracy_min' THEN threshold_value END) AS forecast_accuracy_min,
        max(CASE WHEN threshold_name = 'pipeline_coverage_min' THEN threshold_value END) AS pipeline_coverage_min,
        max(CASE WHEN threshold_name = 'customer_top10_concentration_max' THEN threshold_value END) AS concentration_max,
        max(CASE WHEN threshold_name = 'customer_margin_deterioration_bps' THEN threshold_value END) AS customer_margin_deterioration_bps
    FROM config_management_thresholds
), issues AS (
    SELECT
        'ISS-MARGIN-' || replace(k.period, '-', '') AS issue_id,
        k.period,
        'Margin Deterioration' AS issue_type,
        'Company' AS entity_type,
        'Company Total' AS entity_name,
        'Gross Margin YoY Change (bps)' AS metric,
        k.gross_margin_yoy_bps AS actual_value,
        -t.margin_deterioration_bps AS threshold,
        CASE WHEN k.gross_margin_yoy_bps < -2 * t.margin_deterioration_bps THEN 'High' ELSE 'Medium' END AS severity,
        'Revenue YoY ' || round(k.revenue_yoy_pct * 100, 1)::VARCHAR || '%' AS supporting_metric,
        'Open' AS status
    FROM mart_executive_kpis k CROSS JOIN thresholds t
    WHERE k.gross_margin_yoy_bps < -t.margin_deterioration_bps
    UNION ALL
    SELECT
        'ISS-FORECAST-' || replace(f.period, '-', '') || '-' || upper(f.entity_name),
        f.period,
        'Forecast Accuracy Deterioration',
        f.entity_type,
        f.entity_name,
        'Forecast Accuracy',
        f.forecast_accuracy_pct,
        t.forecast_accuracy_min,
        CASE WHEN f.forecast_accuracy_pct < t.forecast_accuracy_min - 0.10 THEN 'High' ELSE 'Medium' END,
        'Bias ' || round(f.bias_pct * 100, 1)::VARCHAR || '%',
        'Open'
    FROM mart_forecast_accuracy_v2 f CROSS JOIN thresholds t
    WHERE f.entity_type = 'Region' AND f.forecast_accuracy_pct < t.forecast_accuracy_min
    UNION ALL
    SELECT
        'ISS-PIPELINE-' || replace(k.period, '-', ''),
        k.period,
        'Pipeline Coverage Weakness',
        'Company',
        'Company Total',
        'Weighted Pipeline Coverage',
        k.pipeline_coverage,
        t.pipeline_coverage_min,
        CASE WHEN k.pipeline_coverage < t.pipeline_coverage_min - 0.15 THEN 'High' ELSE 'Medium' END,
        'Weighted pipeline ' || round(k.weighted_pipeline, 0)::VARCHAR,
        'Open'
    FROM mart_executive_kpis k CROSS JOIN thresholds t
    WHERE k.pipeline_coverage < t.pipeline_coverage_min
    UNION ALL
    SELECT
        'ISS-OPEX-' || replace(o.period, '-', '') || '-' || upper(replace(o.department_name || '-' || o.account_name, ' ', '-')),
        o.period,
        'Structural OpEx Overrun',
        'Department / Account',
        o.department_name || ' / ' || o.account_name,
        'Forecast Variance',
        o.forecast_variance,
        -(SELECT threshold_value FROM config_management_thresholds WHERE threshold_name = 'opex_variance_material_amount'),
        CASE WHEN abs(o.forecast_variance) >= 2 * (SELECT threshold_value FROM config_management_thresholds WHERE threshold_name = 'opex_variance_material_amount') THEN 'High' ELSE 'Medium' END,
        o.material_unfavorable_months_trailing_6::VARCHAR || ' material months in trailing 6',
        'Open'
    FROM mart_opex_management_v2 o
    WHERE o.variance_classification = 'Structural Overrun'
    UNION ALL
    SELECT
        'ISS-CUSTOMER-' || c.year::VARCHAR || '-' || c.customer_id,
        c.year::VARCHAR || '-12',
        'Customer Profitability Deterioration',
        'Customer',
        c.customer_name,
        'Gross Margin Change (bps)',
        c.margin_change_bps,
        -t.customer_margin_deterioration_bps,
        CASE WHEN c.margin_change_bps < -2 * t.customer_margin_deterioration_bps THEN 'High' ELSE 'Medium' END,
        'Revenue rank ' || c.revenue_rank::VARCHAR,
        'Open'
    FROM mart_customer_profitability_v2 c CROSS JOIN thresholds t
    WHERE c.revenue_rank <= 10 AND c.margin_change_bps < -t.customer_margin_deterioration_bps
    UNION ALL
    SELECT
        'ISS-CONCENTRATION-' || replace(c.period, '-', ''),
        c.period,
        'Customer Concentration Risk',
        'Company',
        'Company Total',
        'Top 10 Customer Revenue Share',
        c.top_10_revenue_pct,
        t.concentration_max,
        CASE WHEN c.top_10_revenue_pct > t.concentration_max + 0.10 THEN 'High' ELSE 'Medium' END,
        'HHI ' || round(c.hhi, 0)::VARCHAR,
        'Monitor'
    FROM mart_customer_concentration_v2 c CROSS JOIN thresholds t
    WHERE c.top_10_revenue_pct > t.concentration_max
)
SELECT * FROM issues;
