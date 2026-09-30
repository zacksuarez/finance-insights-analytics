SELECT
    period,
    department_name,
    account_name,
    actual_amount,
    forecast_amount,
    forecast_variance,
    forecast_variance_pct,
    sum(forecast_variance) OVER (
        PARTITION BY department_name, account_name ORDER BY period ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS rolling_3m_variance,
    dense_rank() OVER (PARTITION BY period ORDER BY forecast_variance ASC) AS unfavorable_variance_rank
FROM mart_department_opex
ORDER BY period, unfavorable_variance_rank;
