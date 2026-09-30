WITH annual AS (
    SELECT year, customer_id, customer_name, sum(revenue) AS revenue
    FROM mart_customer_profitability
    GROUP BY year, customer_id, customer_name
), ranked AS (
    SELECT *,
           dense_rank() OVER (PARTITION BY year ORDER BY revenue DESC) AS revenue_rank,
           revenue / sum(revenue) OVER (PARTITION BY year) AS revenue_share
    FROM annual
)
SELECT *,
       sum(revenue_share) OVER (
           PARTITION BY year ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS cumulative_revenue_share
FROM ranked
ORDER BY year, revenue_rank;
