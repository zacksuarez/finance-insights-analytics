# Power BI Semantic Model Specification

## Model Objective

Use the V1 conformed star schema as the semantic-model foundation and V2 marts as validation/export layers. The recommended Power BI model imports the five dimensions and four facts rather than joining multiple pre-aggregated marts into one ambiguous model.

## Dimensions

- `dim_date`: monthly calendar attributes keyed by `date_key`.
- `dim_customer`: customer, segment, region, industry, owner, contract dates, and status.
- `dim_product`: product name and revenue stream.
- `dim_department`: department and functional group.
- `dim_account`: account, category, financial-statement line, and display order.

## Facts

- `fact_actuals`: one ERP posting; measure `amount`.
- `fact_plan`: one scenario-period-account-department-customer-product row; measure `plan_amount`.
- `fact_pipeline`: one opportunity; measures `pipeline_amount` and `probability`.
- `fact_operational_kpi`: one monthly customer or department KPI observation.

## Relationships

| From dimension | To fact | Cardinality | Filter direction | Active |
| --- | --- | --- | --- | --- |
| `dim_date[date_key]` | `fact_actuals[date_key]` | One-to-many | Single | Yes |
| `dim_date[date_key]` | `fact_plan[date_key]` | One-to-many | Single | Yes |
| `dim_date[date_key]` | `fact_pipeline[expected_close_date_key]` | One-to-many | Single | Yes |
| `dim_date[date_key]` | `fact_pipeline[created_date_key]` | One-to-many | Single | No |
| `dim_date[date_key]` | `fact_operational_kpi[date_key]` | One-to-many | Single | Yes |
| `dim_customer[customer_key]` | Customer keys on all four facts | One-to-many | Single | Yes |
| `dim_product[product_key]` | Product keys on actuals, plan, and pipeline | One-to-many | Single | Yes |
| `dim_department[department_key]` | Department keys on actuals, plan, and KPI | One-to-many | Single | Yes |
| `dim_account[account_key]` | Account keys on actuals and plan | One-to-many | Single | Yes |

Use `USERELATIONSHIP` only in created-date pipeline measures. Do not activate both pipeline date relationships simultaneously.

## Nullable Relationships

Customer and product keys are nullable for corporate OpEx. Department keys are nullable for customer KPI rows, and customer keys are nullable for department KPI rows. Power BI retains those fact rows under `(Blank)` dimension members, allowing company totals to reconcile. Do not inner-join them away or map them to unrelated real members.

## Filter Design

- Keep all relationships single-direction from dimensions to facts.
- Avoid bidirectional filters and many-to-many relationships.
- Use measures to compare actual, plan, pipeline, and operational facts.
- Hide surrogate keys and technical row identifiers from report consumers.
- Sort account names by `dim_account[display_order]` where applicable.

## V2 Consumption Tables

The CSV/Parquet outputs in `data/curated/v2/` can support thin reports, Excel review, or validation. If imported alongside the base star, keep them disconnected or use them in a separate composite model to avoid duplicate filter paths.

## Refresh Order

1. Raw source extracts
2. Dimensions
3. Facts
4. V1 finance marts
5. V2 executive marts and issue register
6. Power BI semantic-model refresh
