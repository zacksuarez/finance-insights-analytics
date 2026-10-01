# Representative Power BI Measures

These DAX measures use the physical V1 star-schema columns. Amount signs follow the model: revenue is positive; COGS and OpEx are negative.

```DAX
Actual Amount :=
SUM ( fact_actuals[amount] )

Revenue :=
CALCULATE ( [Actual Amount], dim_account[account_category] = "Revenue" )

Revenue LY :=
CALCULATE ( [Revenue], DATEADD ( dim_date[month_start], -1, YEAR ) )

Revenue YoY % :=
DIVIDE ( [Revenue] - [Revenue LY], [Revenue LY] )

Forecast :=
CALCULATE (
    SUM ( fact_plan[plan_amount] ),
    fact_plan[scenario_version] = "Forecast"
)

Revenue Forecast :=
CALCULATE ( [Forecast], dim_account[account_category] = "Revenue" )

Budget :=
CALCULATE (
    SUM ( fact_plan[plan_amount] ),
    fact_plan[scenario_version] = "Budget"
)

Budget Variance $ :=
[Actual Amount] - [Budget]

Budget Variance % :=
DIVIDE ( [Budget Variance $], ABS ( [Budget] ) )

Forecast Variance $ :=
[Actual Amount] - [Forecast]

Forecast Variance % :=
DIVIDE ( [Forecast Variance $], ABS ( [Forecast] ) )

COGS :=
CALCULATE ( [Actual Amount], dim_account[account_category] = "COGS" )

Gross Profit :=
[Revenue] + [COGS]

Gross Margin % :=
DIVIDE ( [Gross Profit], [Revenue] )

Gross Margin LY :=
CALCULATE ( [Gross Margin %], DATEADD ( dim_date[month_start], -1, YEAR ) )

Gross Margin bps Change :=
( [Gross Margin %] - [Gross Margin LY] ) * 10000

Operating Expense :=
CALCULATE ( [Actual Amount], dim_account[account_category] = "OpEx" )

Operating Contribution :=
[Revenue] + [COGS] + [Operating Expense]

Operating Contribution Margin % :=
DIVIDE ( [Operating Contribution], [Revenue] )

Forecast Accuracy % :=
VAR ErrorAmount = ABS ( [Revenue] - [Revenue Forecast] )
VAR Accuracy = 1 - DIVIDE ( ErrorAmount, ABS ( [Revenue Forecast] ) )
RETURN
    MAX ( 0, Accuracy )

Gross Pipeline :=
SUM ( fact_pipeline[pipeline_amount] )

Weighted Pipeline :=
SUMX (
    fact_pipeline,
    fact_pipeline[pipeline_amount] * fact_pipeline[probability]
)

Pipeline Coverage :=
DIVIDE ( [Weighted Pipeline], [Revenue Forecast] )

Top 10 Customer Revenue % :=
VAR CustomerSet =
    TOPN (
        10,
        ALLSELECTED ( dim_customer[customer_id] ),
        [Revenue], DESC,
        dim_customer[customer_id], ASC
    )
VAR TopTenRevenue = CALCULATE ( [Revenue], KEEPFILTERS ( CustomerSet ) )
VAR SelectedRevenue =
    CALCULATE ( [Revenue], ALLSELECTED ( dim_customer[customer_id] ) )
RETURN
    DIVIDE ( TopTenRevenue, SelectedRevenue )
```

`Forecast Variance` is context-sensitive: on a revenue visual it compares revenue; on an account or total P&L visual it compares the corresponding account context. Operating Contribution is used instead of EBITDA because V1 does not separately model depreciation, amortization, interest, or taxes.
