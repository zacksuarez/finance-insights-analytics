# Excel Consumption Guide

## Curated Exports

Finance users can open or import the CSV files in `data/curated/v2/` directly. Parquet versions preserve data types and are preferred for Power Query or Fabric ingestion when supported.

Recommended Excel tables:

- `executive_kpis`: monthly management scorecard and trend pivots.
- `customer_profitability`: customer ranking, segmentation, and margin analysis.
- `forecast_accuracy`: region and department/account accuracy pivots.
- `opex_management`: variance review with structural/timing classification.
- `management_issue_register`: filtered management-action list.
- `scenario_analysis`: Base/Upside/Downside what-if comparison.

## PivotTable Workflow

1. Use **Data > Get Data > From Text/CSV** for a curated CSV.
2. Load through Power Query and explicitly set period, numeric, and percentage types.
3. Add the result to the Data Model when combining multiple tables.
4. Build PivotTables with period on rows, entity dimensions on filters, and finance measures in values.
5. Refresh after rerunning `scripts/build_v2_outputs.py`.

Do not join customer, regional, and company-level exports solely on period; their grains differ. Use one output at a time or use the conformed star schema.

## Analyze in Excel

When the star schema is deployed as a Power BI or Fabric semantic model, **Analyze in Excel** gives finance users governed measures, shared definitions, and live PivotTables without copying business logic into workbooks.

## Future Fabric Connectivity

The same approach can connect Excel to a Fabric semantic model or Warehouse. OneLake shortcuts or Power Query can consume Parquet outputs, while centrally governed DAX measures remain in the semantic model.

## Controls

- Retain the generated period and grain fields in extracts.
- Do not replace null percentages caused by zero denominators with zero.
- Preserve the model sign convention.
- Reconcile workbook totals to `executive_kpis` or `mart_reconciliation` before distribution.
