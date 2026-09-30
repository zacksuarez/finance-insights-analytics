CREATE OR REPLACE TABLE fact_actuals AS
SELECT
    e.transaction_id,
    d.date_key,
    a.account_key,
    dep.department_key,
    c.customer_key,
    p.product_key,
    e.date::DATE AS transaction_date,
    e.vendor,
    e.amount::DECIMAL(18, 2) AS amount
FROM stg_erp_transactions e
JOIN dim_date d ON e.period = d.period
JOIN dim_account a ON e.account = a.account_name
JOIN dim_department dep ON e.department = dep.department_name
LEFT JOIN dim_customer c ON e.customer_id = c.customer_id
LEFT JOIN dim_product p ON e.product_id = p.product_id;

CREATE OR REPLACE TABLE fact_plan AS
SELECT
    row_number() OVER (
        ORDER BY ep.scenario_version, ep.period, ep.account, ep.department,
                 coalesce(ep.customer_id, ''), coalesce(ep.product_id, '')
    )::BIGINT AS plan_key,
    d.date_key,
    a.account_key,
    dep.department_key,
    c.customer_key,
    p.product_key,
    ep.scenario_version,
    ep.forecast_amount::DECIMAL(18, 2) AS plan_amount
FROM stg_epm_plan ep
JOIN dim_date d ON ep.period = d.period
JOIN dim_account a ON ep.account = a.account_name
JOIN dim_department dep ON ep.department = dep.department_name
LEFT JOIN dim_customer c ON ep.customer_id = c.customer_id
LEFT JOIN dim_product p ON ep.product_id = p.product_id;

CREATE OR REPLACE TABLE fact_pipeline AS
SELECT
    s.opportunity_id,
    created.date_key AS created_date_key,
    expected.date_key AS expected_close_date_key,
    c.customer_key,
    p.product_key,
    s.stage,
    s.pipeline_amount::DECIMAL(18, 2) AS pipeline_amount,
    s.probability::DECIMAL(6, 4) AS probability,
    s.region
FROM stg_sales_pipeline s
JOIN dim_date created ON strftime(s.created_date::DATE, '%Y-%m') = created.period
JOIN dim_date expected ON strftime(s.expected_close_date::DATE, '%Y-%m') = expected.period
JOIN dim_customer c ON s.customer_id = c.customer_id
JOIN dim_product p ON s.product_id = p.product_id;

CREATE OR REPLACE TABLE fact_operational_kpi AS
SELECT
    row_number() OVER (
        ORDER BY k.period, k.record_type, coalesce(k.customer_id, ''), coalesce(k.department, '')
    )::BIGINT AS kpi_key,
    d.date_key,
    k.record_type,
    c.customer_key,
    dep.department_key,
    k.active_users::INTEGER AS active_users,
    k.support_tickets::INTEGER AS support_tickets,
    k.implementation_hours::INTEGER AS implementation_hours,
    k.usage_metric::DECIMAL(18, 2) AS usage_metric,
    k.headcount::INTEGER AS headcount
FROM stg_operational_kpis k
JOIN dim_date d ON k.period = d.period
LEFT JOIN dim_customer c ON k.customer_id = c.customer_id
LEFT JOIN dim_department dep ON k.department = dep.department_name;

CREATE UNIQUE INDEX fact_actuals_pk ON fact_actuals(transaction_id);
CREATE UNIQUE INDEX fact_plan_pk ON fact_plan(plan_key);
CREATE UNIQUE INDEX fact_pipeline_pk ON fact_pipeline(opportunity_id);
CREATE UNIQUE INDEX fact_operational_kpi_pk ON fact_operational_kpi(kpi_key);
