# Power BI Executive Report Design

This specification defines four decision-oriented pages. It does not claim that a `.pbix` file has been built or deployed.

## Page 1 — Executive Overview

| Business question | Visual | Measures | Dimensions | Management interpretation |
| --- | --- | --- | --- | --- |
| Are we growing profitably? | KPI cards | Revenue, Revenue YoY %, Gross Margin %, Gross Margin bps Change, Operating Contribution | Latest period | Separate growth from margin and contribution quality. |
| How are revenue and margin moving? | Combo line chart | Revenue, Gross Margin % | Month | Detect growth/margin divergence and inflection points. |
| Are results tracking plan? | Variance waterfall or clustered columns | Forecast Variance $, Budget Variance $ | Financial-statement line | Locate material plan gaps without mixing signs. |
| What needs attention now? | Issue-register table | Actual value, threshold, severity | Issue type, entity, period | Prioritize deterministic rule breaches. |
| Is the forward commercial base sufficient? | Line chart with threshold | Pipeline Coverage, 0.75x reference | Month | Assess trend and current coverage against forecast revenue. |

## Page 2 — Customer & Profitability

| Business question | Visual | Measures | Dimensions | Management interpretation |
| --- | --- | --- | --- | --- |
| Which customers create value? | Scatter plot | Revenue, Gross Margin %, Gross Profit | Customer; size by revenue; color by profitability segment | Separate scale from margin quality. |
| Which large customers are deteriorating? | Ranked table | Revenue, Margin Change bps, Gross Profit Growth % | Customer, region, segment | Focus account reviews on material deterioration. |
| How concentrated is the business? | KPI and trend line | Top 1 %, Top 5 %, Top 10 %, HHI | Month | Monitor dependence on the largest relationships. |
| What is changing for one customer? | Drill-through trend | Revenue, Gross Profit, Gross Margin %, support tickets, implementation hours | Month, selected customer | Compare financial trend with observed operational load. |

## Page 3 — Forecast & Operations

| Business question | Visual | Measures | Dimensions | Management interpretation |
| --- | --- | --- | --- | --- |
| Where is forecast accuracy deteriorating? | Heat map | Forecast Accuracy %, Bias %, 3M MAPE | Region by month | Distinguish persistent bias from isolated misses. |
| Which expenses are structurally above plan? | Matrix with status | Actual, Forecast, Variance $, YTD Variance | Department, account | Separate structural overruns from potential timing. |
| How persistent is the issue? | Small-multiple line chart | Rolling 3M Forecast Variance | Department/account, month | Verify repeated misses before escalation. |
| Which regions are improving? | Ranked table | Revenue YoY %, Gross Margin %, Forecast Accuracy %, Pipeline Coverage | Region | Compare performance and forward risk in one view. |

## Page 4 — Pipeline & Forward Outlook

| Business question | Visual | Measures | Dimensions | Management interpretation |
| --- | --- | --- | --- | --- |
| Is pipeline sufficient by expected close period? | Line and column chart | Weighted Pipeline, Revenue Forecast, Pipeline Coverage | Expected close month | Compare probability-weighted pipeline with supported revenue requirements. |
| What is the quality of pipeline? | 100% stacked columns | Gross Pipeline | Stage, expected close month | Reveal stage mix and low-probability dependence. |
| Where is pipeline weakening? | Regional small multiples | Weighted Pipeline, Pipeline Coverage | Region, month | Find geographic deterioration before revenue impact. |
| What is the management range? | Scenario table or waterfall | Scenario Revenue, Gross Profit, OpEx, Operating Contribution | Base/Upside/Downside | Compare explicit what-if assumptions; do not present as prediction. |

## Interaction Guidance

Use synchronized period, region, segment, product, department, and account slicers where relevant. Keep issue-register selection available for drill-through. Use accessible status labels in addition to color, and preserve negative signs for COGS and OpEx in detailed financial views.
