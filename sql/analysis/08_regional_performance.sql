SELECT
    period,
    region,
    actual_revenue,
    budget_revenue,
    forecast_revenue,
    forecast_variance,
    absolute_forecast_error_pct,
    actual_revenue / sum(actual_revenue) OVER (PARTITION BY period) AS revenue_share,
    sum(actual_revenue) OVER (
        PARTITION BY region ORDER BY period ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS rolling_3m_revenue
FROM mart_regional_performance
ORDER BY period, region;
