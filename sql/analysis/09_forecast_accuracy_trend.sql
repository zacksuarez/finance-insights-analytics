SELECT
    period,
    region,
    actual_revenue,
    forecast_revenue,
    absolute_forecast_error_pct,
    avg(absolute_forecast_error_pct) OVER (
        PARTITION BY region ORDER BY period ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS rolling_3m_error_pct,
    absolute_forecast_error_pct - lag(absolute_forecast_error_pct, 3) OVER (
        PARTITION BY region ORDER BY period
    ) AS error_change_vs_3m_prior
FROM mart_regional_performance
ORDER BY region, period;
