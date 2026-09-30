SELECT
    period,
    customer_id,
    customer_name,
    revenue,
    gross_profit,
    gross_margin_pct,
    avg(gross_margin_pct) OVER (
        PARTITION BY customer_id ORDER BY period ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS gross_margin_3m_average,
    gross_margin_pct - lag(gross_margin_pct, 12) OVER (
        PARTITION BY customer_id ORDER BY period
    ) AS gross_margin_yoy_change
FROM mart_customer_profitability
ORDER BY customer_id, period;
