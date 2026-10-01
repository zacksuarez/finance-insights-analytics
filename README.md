# Finance Insights & Analytics

Finance Insights & Analytics is a portable FP&A platform that unifies fictional ERP, CRM, EPM, sales-pipeline, and operational data into trusted, decision-ready analytics. V1 establishes the reproducible data foundation; V2 adds deterministic executive metrics, management issues, scenarios, and a professional Power BI/Excel semantic-model specification without AI or cloud dependencies.

## Business Problem

Finance teams often reconcile fragmented accounting, planning, customer, pipeline, and operating data before they can answer management questions. This project demonstrates how those sources can become a reusable decision-support layer for revenue, margin, customer profitability, forecast accuracy, pipeline coverage, and operating-expense analysis.

The scenario represents a fictional North American B2B technology and services company with approximately $100M-$150M in annual revenue, 150 customers, three regions, three customer segments, four revenue streams, and five departments.

## Architecture

```text
Fictional source-system exports
  ERP | CRM | EPM | Sales Pipeline | Operational KPIs
                         |
                         v
                 DuckDB staging views
                         |
                         v
             Conformed dimensional model
        dimensions + actual/plan/pipeline/KPI facts
                         |
                         v
             Curated FP&A analytical marts
                         |
                         v
       Reusable SQL analysis + CSV materializations
                         |
                         v
       Executive marts + deterministic issues
                         |
                         v
          Power BI / Excel semantic foundation
```

Raw exports in `data/raw/` intentionally retain source-system differences. Curated data in `data/curated/` is modeled separately and never replaces the source evidence.

## Source Systems

- **ERP:** accounting actuals for revenue, COGS, payroll, software, marketing, travel, professional services, facilities, and other OpEx.
- **CRM:** customer master, segment, region, industry, owner, contract dates, and status.
- **EPM:** Budget and rolling Forecast values at an appropriate finance grain.
- **Sales pipeline:** opportunity amount, stage, probability, expected close date, product, customer, and region.
- **Operational KPIs:** customer users, usage, support tickets, implementation hours, and department headcount.

All entities are fictional. Generation uses the fixed seed `20260930`; `data/raw/manifest.json` records row counts and SHA-256 hashes for reproducibility.

## Data Model

The DuckDB model contains:

- Dimensions: `dim_date`, `dim_customer`, `dim_product`, `dim_department`, `dim_account`
- Facts: `fact_actuals`, `fact_plan`, `fact_pipeline`, `fact_operational_kpi`
- Marts: monthly P&L, finance variance, customer profitability, regional performance, pipeline coverage, department OpEx, and reconciliation

Every fact grain and relationship boundary is documented in [docs/data-model.md](docs/data-model.md). Revenue uses a positive sign; COGS and OpEx use negative signs.

## Embedded Business Scenarios

The synthetic data contains intentionally designed management issues rather than random noise. They include growth with margin pressure, customer-level profitability deterioration, regional forecast degradation, weakening pipeline coverage, structural OpEx overspend, and customer concentration.

The top-level project leaves those issues for the analytical queries to reveal. The complete developer truth manifest is in [docs/business-scenarios.md](docs/business-scenarios.md) so tests can prove the stories remain present.

## Analytics

Fourteen independent SQL analyses cover:

1. Monthly P&L trend
2. Actual vs Forecast variance
3. Actual vs Budget variance
4. Revenue growth by customer
5. Customer profitability
6. Customer gross-margin trend
7. Product and revenue mix
8. Regional performance
9. Forecast-accuracy trend
10. Pipeline-coverage trend
11. Department OpEx variance
12. Customer concentration
13. Top and bottom profitability movers
14. Operational-driver relationships

The queries in `sql/analysis/` use CTEs, windows, rolling averages, lag comparisons, ranking, percent-of-total, and trend logic. They materialize to reviewer-friendly CSVs in `data/curated/analysis/`.

Price/volume/mix is intentionally excluded because V1 does not simulate reliable invoice quantities and realized unit prices. [The model documentation](docs/data-model.md#price--volume--mix-boundary) identifies the source fields required for a defensible future PVM analysis.

## Data Quality & Reconciliation

The build fails on duplicate keys, missing required dimensions, invalid customer/product relationships, invalid plan versions, impossible probabilities or KPIs, and source-to-model reconciliation differences.

Control totals prove:

```text
ERP actuals = fact_actuals = mart_finance_monthly actuals
EPM Budget  = fact_plan Budget  = mart_finance_monthly Budget
EPM Forecast = fact_plan Forecast = mart_finance_monthly Forecast
```

Automated tests also verify reproducibility, source volumes, dimensional integrity, all six embedded business patterns, and execution of every required analysis.

## Power BI / Excel Readiness

The conformed dimensions and facts map directly to a Power BI semantic model using one-to-many relationships. Curated marts can be imported into Power BI, queried from Excel through DuckDB-compatible tooling, or exported as CSV for standard Excel workflows. Surrogate keys support stable relationships, while business keys preserve source traceability.

V2 includes a semantic-model specification, representative DAX measures, a four-page executive report design, and an Excel consumption guide. It does not include or claim a physically deployed `.pbix` file.

## V2 — Executive Analytics

V2 turns the trusted V1 model into a management decision layer while preserving all source, fact, reconciliation, and business-story controls.

- **Executive KPIs:** Monthly revenue, growth, plan variance, margin, operating contribution, concentration, forecast accuracy, and pipeline coverage.
- **Customer profitability:** Revenue and gross-profit growth, margin movement, concentration, ranking, trend, and deterministic portfolio segments.
- **Margin analytics:** Product, region, and customer-segment mix/margin bridge. This is not represented as full PVM.
- **Forecast accuracy:** Absolute error, percentage error, MAPE, bias, and rolling 3/6-month views at company, region, and department/account levels.
- **Pipeline:** Gross and weighted pipeline, stage mix, growth, expected-close timing, and coverage against forecast revenue.
- **OpEx management:** Actual/Budget/Forecast variance, rolling and YTD variance, and persistence-based structural/timing classification.
- **Management issues:** Threshold-backed issue register with entity, metric, severity, supporting evidence, and status.
- **Scenarios:** Explicit Base/Upside/Downside assumptions applied to the latest full-year baseline.
- **Consumption:** Selective V2 tables materialized as CSV and compressed Parquet for Power BI, Excel, and future governed analytics.

The deterministic [management insight pack](outputs/management-insight-pack.md) summarizes trusted V2 outputs with templates only. It does not speculate about unsupported causes.

Supporting specifications:

- [Management rules and scenario assumptions](docs/management-rules.md)
- [Power BI semantic model](docs/power-bi-semantic-model.md)
- [Power BI measures](docs/power-bi-measures.md)
- [Power BI page design](docs/power-bi-page-design.md)
- [Excel consumption](docs/excel-consumption.md)

## Microsoft Portability

| Local component | Microsoft destination |
| --- | --- |
| Python source generation and output scripts | Fabric notebooks or Fabric Data Factory/Pipelines |
| CSV and compressed Parquet | OneLake or ADLS |
| DuckDB | Fabric Warehouse, Fabric Lakehouse SQL endpoint, or Azure SQL |
| SQL transformations and executive marts | Fabric SQL, notebooks, or pipelines |
| Curated star schema | Power BI semantic model |
| Executive outputs and issue register | Power BI, Excel, and Microsoft 365 consumption |

This mapping is architectural guidance only; V2 does not provision or require Microsoft cloud services.

## How to Run

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts/generate_data.py
python scripts/build_model.py
python scripts/validate_data.py
python scripts/run_analyses.py
python scripts/build_v2_outputs.py
python scripts/generate_insight_pack.py
python -m unittest discover -s tests -v
```

Run the commands from the repository root. Re-running generation with the same seed produces byte-identical source CSVs.

## Project Roadmap

- V1 — Data foundation & analytical model — COMPLETE
- V2 — Executive analytics & Power BI readiness — COMPLETE
- V3 — AI-assisted insight generation

V2 contains no AI, OpenAI integration, RAG, agents, fabricated Power BI files, cloud infrastructure, or confidential data.

## Portfolio Purpose

This project demonstrates how a modern FP&A or Finance Analytics leader can unify fragmented financial and operational data into a controlled decision-support layer. It emphasizes finance logic, dimensional architecture, reconciliation, analytically meaningful SQL, reproducibility, and technology portability before visualization or AI is introduced.
