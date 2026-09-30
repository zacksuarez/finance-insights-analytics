WITH pnl AS (
    SELECT *,
           avg(revenue) OVER (ORDER BY period ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS revenue_3m_average,
           lag(revenue, 12) OVER (ORDER BY period) AS prior_year_revenue,
           lag(gross_margin_pct, 12) OVER (ORDER BY period) AS prior_year_gross_margin_pct
    FROM mart_monthly_pnl
)
SELECT *,
       revenue - prior_year_revenue AS revenue_yoy_change,
       CASE WHEN prior_year_revenue = 0 THEN NULL ELSE revenue / prior_year_revenue - 1 END AS revenue_yoy_pct,
       gross_margin_pct - prior_year_gross_margin_pct AS gross_margin_yoy_change
FROM pnl
WHERE period >= '2024-01'
ORDER BY period;
