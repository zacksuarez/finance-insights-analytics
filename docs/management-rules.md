# V2 Management Rules and Scenario Assumptions

V2 uses explicit deterministic rules stored in `config_management_thresholds`. These values are portfolio/demo assumptions. In a production implementation, Finance would own approval, effective dating, and periodic review.

## Central Thresholds

| Threshold | Default | Use |
| --- | ---: | --- |
| Revenue variance materiality | 5% | Flags material revenue variance context. |
| Gross-margin deterioration | 200 bps | Opens a company margin-deterioration issue. |
| Minimum forecast accuracy | 85% | Opens a regional forecast-accuracy issue. |
| Minimum weighted pipeline coverage | 0.75x | Opens a company pipeline-coverage issue. |
| Maximum top-10 customer concentration | 25% | Opens a concentration monitor item. |
| Customer margin deterioration | 500 bps | Flags top-10 customers with material margin erosion. |
| Low customer growth | 5% | Supports customer profitability segmentation. |
| OpEx monthly variance | 5% or $10,000 | Defines a material unfavorable expense month. |
| OpEx persistence | 4 of trailing 6 months | Classifies a material unfavorable pattern as structural. |

## Issue Register Rules

- **Margin deterioration:** Company gross-margin YoY change is below `-200 bps`.
- **Forecast accuracy deterioration:** Regional forecast accuracy is below `85%`.
- **Pipeline weakness:** Company weighted pipeline divided by forecast revenue is below `0.75x`.
- **Structural OpEx overrun:** The current department/account variance is materially unfavorable and at least four of the trailing six months are materially unfavorable.
- **Customer profitability deterioration:** A top-10 revenue customer loses more than `500 bps` of gross margin YoY.
- **Customer concentration risk:** Top-10 customers exceed `25%` of company revenue.

High severity indicates a wider breach than the base threshold. Rules identify conditions for investigation; they do not infer operational root causes.

## Forecast Accuracy

```text
Forecast Error = Actual - Forecast
Absolute Error % = abs(Actual - Forecast) / abs(Forecast)
Forecast Accuracy % = max(0, 1 - Absolute Error %)
Bias % = (Actual - Forecast) / abs(Forecast)
```

Rolling 3- and 6-month MAPE are simple averages of monthly absolute error percentages. Zero forecast denominators return null.

## Customer Concentration

Top-N percentages divide ranked customer revenue by total company revenue for the same period. HHI is the sum of squared customer shares multiplied by 10,000. HHI is a directional portfolio indicator here; standard competition-policy interpretations should not be applied without market-share data.

## Margin Bridge

V2 decomposes annual gross-margin movement by product, region, and customer segment:

```text
Mix Effect bps = (Current Mix - Prior Mix) * Prior Margin * 10,000
Margin-Rate Effect bps = Current Mix * (Current Margin - Prior Margin) * 10,000
```

This is a supported mix/margin bridge, not price-volume-mix. V1 lacks invoice quantity, realized unit price, list price, and discount fields required for defensible PVM.

## Scenario Assumptions

| Scenario | Revenue growth | Gross-margin change | OpEx growth |
| --- | ---: | ---: | ---: |
| Base | 5% | 0 bps | 4% |
| Upside | 10% | +150 bps | 3% |
| Downside | -2% | -200 bps | 6% |

Scenarios apply assumptions to the latest full-year actual baseline. They are deterministic management what-if calculations, not forecasts or predictive models.
