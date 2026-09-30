CREATE OR REPLACE TABLE mart_finance_monthly AS
WITH actual AS (
    SELECT date_key, account_key, department_key, customer_key, product_key, sum(amount) AS actual_amount
    FROM fact_actuals
    GROUP BY ALL
), plan AS (
    SELECT
        date_key,
        account_key,
        department_key,
        customer_key,
        product_key,
        sum(CASE WHEN scenario_version = 'Budget' THEN plan_amount ELSE 0 END) AS budget_amount,
        sum(CASE WHEN scenario_version = 'Forecast' THEN plan_amount ELSE 0 END) AS forecast_amount
    FROM fact_plan
    GROUP BY ALL
), combined AS (
    SELECT
        coalesce(a.date_key, p.date_key) AS date_key,
        coalesce(a.account_key, p.account_key) AS account_key,
        coalesce(a.department_key, p.department_key) AS department_key,
        coalesce(a.customer_key, p.customer_key) AS customer_key,
        coalesce(a.product_key, p.product_key) AS product_key,
        coalesce(a.actual_amount, 0) AS actual_amount,
        coalesce(p.budget_amount, 0) AS budget_amount,
        coalesce(p.forecast_amount, 0) AS forecast_amount
    FROM actual a
    FULL OUTER JOIN plan p
      ON a.date_key = p.date_key
     AND a.account_key = p.account_key
     AND a.department_key = p.department_key
     AND a.customer_key IS NOT DISTINCT FROM p.customer_key
     AND a.product_key IS NOT DISTINCT FROM p.product_key
)
SELECT
    c.*,
    c.actual_amount - c.budget_amount AS budget_variance,
    c.actual_amount - c.forecast_amount AS forecast_variance,
    CASE WHEN c.budget_amount = 0 THEN NULL ELSE (c.actual_amount - c.budget_amount) / abs(c.budget_amount) END AS budget_variance_pct,
    CASE WHEN c.forecast_amount = 0 THEN NULL ELSE (c.actual_amount - c.forecast_amount) / abs(c.forecast_amount) END AS forecast_variance_pct
FROM combined c;

CREATE OR REPLACE VIEW mart_monthly_pnl AS
SELECT
    d.period,
    d.year,
    sum(CASE WHEN a.account_category = 'Revenue' THEN f.actual_amount ELSE 0 END) AS revenue,
    sum(CASE WHEN a.account_category = 'COGS' THEN f.actual_amount ELSE 0 END) AS cogs,
    sum(CASE WHEN a.account_category IN ('Revenue', 'COGS') THEN f.actual_amount ELSE 0 END) AS gross_profit,
    CASE
        WHEN sum(CASE WHEN a.account_category = 'Revenue' THEN f.actual_amount ELSE 0 END) = 0 THEN NULL
        ELSE sum(CASE WHEN a.account_category IN ('Revenue', 'COGS') THEN f.actual_amount ELSE 0 END)
             / sum(CASE WHEN a.account_category = 'Revenue' THEN f.actual_amount ELSE 0 END)
    END AS gross_margin_pct,
    sum(CASE WHEN a.account_category = 'OpEx' THEN f.actual_amount ELSE 0 END) AS operating_expense,
    sum(f.actual_amount) AS operating_contribution
FROM mart_finance_monthly f
JOIN dim_date d USING (date_key)
JOIN dim_account a USING (account_key)
GROUP BY d.period, d.year;

CREATE OR REPLACE VIEW mart_customer_profitability AS
WITH financials AS (
    SELECT
        f.date_key,
        f.customer_key,
        sum(CASE WHEN a.account_category = 'Revenue' THEN f.amount ELSE 0 END) AS revenue,
        sum(CASE WHEN a.account_category = 'COGS' THEN f.amount ELSE 0 END) AS cogs
    FROM fact_actuals f
    JOIN dim_account a USING (account_key)
    WHERE f.customer_key IS NOT NULL
    GROUP BY f.date_key, f.customer_key
), operational AS (
    SELECT
        date_key,
        customer_key,
        sum(support_tickets) AS support_tickets,
        sum(implementation_hours) AS implementation_hours,
        sum(active_users) AS active_users,
        sum(usage_metric) AS usage_metric
    FROM fact_operational_kpi
    WHERE record_type = 'Customer'
    GROUP BY date_key, customer_key
)
SELECT
    d.period,
    d.year,
    c.customer_id,
    c.customer_name,
    c.segment,
    c.region,
    f.revenue,
    f.cogs,
    f.revenue + f.cogs AS gross_profit,
    CASE WHEN f.revenue = 0 THEN NULL ELSE (f.revenue + f.cogs) / f.revenue END AS gross_margin_pct,
    o.support_tickets,
    o.implementation_hours,
    o.active_users,
    o.usage_metric
FROM financials f
JOIN dim_date d USING (date_key)
JOIN dim_customer c USING (customer_key)
LEFT JOIN operational o USING (date_key, customer_key);

CREATE OR REPLACE VIEW mart_regional_performance AS
SELECT
    d.period,
    c.region,
    sum(CASE WHEN a.account_category = 'Revenue' THEN f.actual_amount ELSE 0 END) AS actual_revenue,
    sum(CASE WHEN a.account_category = 'Revenue' THEN f.budget_amount ELSE 0 END) AS budget_revenue,
    sum(CASE WHEN a.account_category = 'Revenue' THEN f.forecast_amount ELSE 0 END) AS forecast_revenue,
    sum(CASE WHEN a.account_category = 'Revenue' THEN f.actual_amount - f.forecast_amount ELSE 0 END) AS forecast_variance,
    CASE
        WHEN sum(CASE WHEN a.account_category = 'Revenue' THEN abs(f.forecast_amount) ELSE 0 END) = 0 THEN NULL
        ELSE sum(CASE WHEN a.account_category = 'Revenue' THEN abs(f.actual_amount - f.forecast_amount) ELSE 0 END)
             / sum(CASE WHEN a.account_category = 'Revenue' THEN abs(f.forecast_amount) ELSE 0 END)
    END AS absolute_forecast_error_pct
FROM mart_finance_monthly f
JOIN dim_date d USING (date_key)
JOIN dim_account a USING (account_key)
JOIN dim_customer c USING (customer_key)
GROUP BY d.period, c.region;

CREATE OR REPLACE VIEW mart_pipeline_coverage AS
WITH pipeline AS (
    SELECT
        d.period,
        p.region,
        sum(p.pipeline_amount) AS gross_pipeline,
        sum(p.pipeline_amount * p.probability) AS weighted_pipeline
    FROM fact_pipeline p
    JOIN dim_date d ON p.expected_close_date_key = d.date_key
    GROUP BY d.period, p.region
), revenue AS (
    SELECT period, region, actual_revenue
    FROM mart_regional_performance
)
SELECT
    p.period,
    p.region,
    p.gross_pipeline,
    p.weighted_pipeline,
    r.actual_revenue,
    CASE WHEN r.actual_revenue = 0 THEN NULL ELSE p.weighted_pipeline / r.actual_revenue END AS weighted_pipeline_coverage
FROM pipeline p
JOIN revenue r USING (period, region);

CREATE OR REPLACE VIEW mart_department_opex AS
SELECT
    d.period,
    dep.department_name,
    a.account_name,
    f.actual_amount,
    f.budget_amount,
    f.forecast_amount,
    f.actual_amount - f.forecast_amount AS forecast_variance,
    f.forecast_variance_pct
FROM mart_finance_monthly f
JOIN dim_date d USING (date_key)
JOIN dim_department dep USING (department_key)
JOIN dim_account a USING (account_key)
WHERE a.account_category = 'OpEx' AND f.customer_key IS NULL AND f.product_key IS NULL;

CREATE OR REPLACE VIEW mart_reconciliation AS
SELECT
    'Actuals' AS measure,
    (SELECT sum(amount) FROM stg_erp_transactions) AS source_total,
    (SELECT sum(amount) FROM fact_actuals) AS fact_total,
    (SELECT sum(actual_amount) FROM mart_finance_monthly) AS mart_total
UNION ALL
SELECT
    scenario_version,
    (SELECT sum(forecast_amount) FROM stg_epm_plan s WHERE s.scenario_version = p.scenario_version),
    (SELECT sum(plan_amount) FROM fact_plan f WHERE f.scenario_version = p.scenario_version),
    CASE
        WHEN scenario_version = 'Budget' THEN (SELECT sum(budget_amount) FROM mart_finance_monthly)
        ELSE (SELECT sum(forecast_amount) FROM mart_finance_monthly)
    END
FROM (VALUES ('Budget'), ('Forecast')) p(scenario_version);
