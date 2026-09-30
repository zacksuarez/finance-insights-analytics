# V1 Data Model

## Design

The local analytical layer uses a conformed star schema in DuckDB. Raw CSV exports remain immutable inputs; staging views normalize types without changing source grain; dimensions and facts use surrogate keys; finance marts expose measures suited to Power BI, Excel, Fabric, or SQL analysis.

## Dimensions

| Table | Grain | Business key |
| --- | --- | --- |
| `dim_date` | One row per calendar month, including pipeline lookback months | `period` |
| `dim_customer` | One row per CRM customer | `customer_id` |
| `dim_product` | One row per product or revenue stream | `product_id` |
| `dim_department` | One row per organizational department | `department_name` |
| `dim_account` | One row per chart-of-accounts member | `account_name` |

## Facts

| Table | Grain | Primary identifier | Measures |
| --- | --- | --- | --- |
| `fact_actuals` | One ERP posting by transaction, account, department, and optional customer/product | `transaction_id` | `amount` |
| `fact_plan` | One scenario-period-account-department-customer-product plan row | `plan_key` | `plan_amount` |
| `fact_pipeline` | One CRM opportunity | `opportunity_id` | `pipeline_amount`, `probability` |
| `fact_operational_kpi` | One period-record type-customer or department KPI observation | `kpi_key` | users, tickets, hours, usage, headcount |

Nullable customer and product keys are intentional for corporate operating expenses. Customer and product foreign keys are mandatory where the source record carries those business keys. The monthly finance mart joins facts only at their shared dimensional grain, preventing accidental many-to-many multiplication.

## Curated Layer

- `mart_finance_monthly`: actual, Budget, Forecast, and variance measures at the common finance grain.
- `mart_monthly_pnl`: monthly revenue, COGS, gross profit, gross margin, OpEx, and operating contribution.
- `mart_customer_profitability`: monthly customer revenue, gross profit, gross margin, and operational drivers.
- `mart_regional_performance`: regional revenue and forecast accuracy.
- `mart_pipeline_coverage`: gross and probability-weighted pipeline coverage.
- `mart_department_opex`: department/category actual-to-plan performance.
- `mart_reconciliation`: source-to-fact-to-mart control totals.

## Sign Convention

Revenue is positive. COGS and operating expenses are negative. Gross profit and operating contribution therefore reconcile through addition. An unfavorable expense variance is negative when actual expense is more negative than plan.

## Semantic-Model Foundation

Power BI or Excel should load the five dimensions and four facts, use one-to-many single-direction relationships from dimensions to facts, and source management measures from the curated marts where practical. Hide surrogate keys from report consumers and retain business keys for traceability.

## Price / Volume / Mix Boundary

V1 does not present a PVM calculation because the simulated sources do not contain a defensible unit quantity, contracted list price, realized unit price, or explicit discount field at invoice-line grain. A valid future PVM model would require those fields plus consistent units of measure and product/customer price effective dates.
