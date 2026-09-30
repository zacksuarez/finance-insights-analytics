CREATE OR REPLACE TABLE dim_date AS
WITH months AS (
    SELECT month_start::DATE AS month_start
    FROM generate_series(DATE '2023-08-01', DATE '2025-12-01', INTERVAL 1 MONTH) dates(month_start)
)
SELECT
    CAST(strftime(month_start, '%Y%m') AS INTEGER) AS date_key,
    strftime(month_start, '%Y-%m') AS period,
    month_start,
    EXTRACT(year FROM month_start)::INTEGER AS year,
    EXTRACT(quarter FROM month_start)::INTEGER AS quarter,
    EXTRACT(month FROM month_start)::INTEGER AS month_number,
    strftime(month_start, '%B') AS month_name,
    'FY' || EXTRACT(year FROM month_start)::VARCHAR AS fiscal_year
FROM months;

CREATE OR REPLACE TABLE dim_customer AS
SELECT
    row_number() OVER (ORDER BY customer_id)::INTEGER AS customer_key,
    customer_id,
    customer_name,
    segment,
    region,
    industry,
    account_owner,
    contract_start::DATE AS contract_start,
    contract_end::DATE AS contract_end,
    status
FROM stg_crm_customers;

CREATE OR REPLACE TABLE dim_product AS
SELECT * FROM (
    VALUES
        (1, 'PROD-PLATFORM', 'Platform Subscription', 'Recurring Revenue'),
        (2, 'PROD-ANALYTICS', 'Analytics Module', 'Recurring Revenue'),
        (3, 'PROD-PRO_SERVICES', 'Professional Services', 'Services Revenue'),
        (4, 'PROD-IMPLEMENTATION', 'Implementation Services', 'Services Revenue')
) products(product_key, product_id, product_name, revenue_stream);

CREATE OR REPLACE TABLE dim_department AS
SELECT * FROM (
    VALUES
        (1, 'Sales', 'Go-to-Market'),
        (2, 'Marketing', 'Go-to-Market'),
        (3, 'Customer Success', 'Service Delivery'),
        (4, 'Engineering', 'Product & Technology'),
        (5, 'G&A', 'Corporate')
) departments(department_key, department_name, functional_group);

CREATE OR REPLACE TABLE dim_account AS
WITH accounts AS (
    SELECT DISTINCT account, account_category FROM stg_erp_transactions
)
SELECT
    row_number() OVER (ORDER BY
        CASE account_category WHEN 'Revenue' THEN 1 WHEN 'COGS' THEN 2 ELSE 3 END,
        account
    )::INTEGER AS account_key,
    account AS account_name,
    account_category,
    CASE
        WHEN account_category = 'Revenue' THEN 'Revenue'
        WHEN account_category = 'COGS' THEN 'Cost of Revenue'
        ELSE 'Operating Expense'
    END AS financial_statement_line,
    CASE account_category WHEN 'Revenue' THEN 1 WHEN 'COGS' THEN 2 ELSE 3 END AS display_order
FROM accounts;

CREATE UNIQUE INDEX dim_date_pk ON dim_date(date_key);
CREATE UNIQUE INDEX dim_customer_pk ON dim_customer(customer_key);
CREATE UNIQUE INDEX dim_customer_id_uk ON dim_customer(customer_id);
CREATE UNIQUE INDEX dim_product_pk ON dim_product(product_key);
CREATE UNIQUE INDEX dim_product_id_uk ON dim_product(product_id);
CREATE UNIQUE INDEX dim_department_pk ON dim_department(department_key);
CREATE UNIQUE INDEX dim_department_name_uk ON dim_department(department_name);
CREATE UNIQUE INDEX dim_account_pk ON dim_account(account_key);
CREATE UNIQUE INDEX dim_account_name_uk ON dim_account(account_name);
