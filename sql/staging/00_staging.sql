CREATE OR REPLACE VIEW stg_erp_transactions AS
SELECT *
FROM read_csv_auto('${RAW_PATH}/erp_transactions.csv', header = true, nullstr = '');

CREATE OR REPLACE VIEW stg_crm_customers AS
SELECT *
FROM read_csv_auto('${RAW_PATH}/crm_customers.csv', header = true, nullstr = '');

CREATE OR REPLACE VIEW stg_epm_plan AS
SELECT *
FROM read_csv_auto('${RAW_PATH}/epm_plan.csv', header = true, nullstr = '');

CREATE OR REPLACE VIEW stg_sales_pipeline AS
SELECT *
FROM read_csv_auto('${RAW_PATH}/sales_pipeline.csv', header = true, nullstr = '');

CREATE OR REPLACE VIEW stg_operational_kpis AS
SELECT *
FROM read_csv_auto('${RAW_PATH}/operational_kpis.csv', header = true, nullstr = '');
