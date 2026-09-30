WITH annual AS (
    SELECT year, customer_id, customer_name, segment, region, sum(revenue) AS revenue
    FROM mart_customer_profitability
    GROUP BY ALL
), compared AS (
    SELECT *, lag(revenue) OVER (PARTITION BY customer_id ORDER BY year) AS prior_year_revenue
    FROM annual
)
SELECT *,
       revenue - prior_year_revenue AS revenue_growth,
       CASE WHEN prior_year_revenue = 0 THEN NULL ELSE revenue / prior_year_revenue - 1 END AS revenue_growth_pct
FROM compared
ORDER BY year, revenue_growth DESC NULLS LAST;
