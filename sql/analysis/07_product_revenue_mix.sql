WITH product_revenue AS (
    SELECT
        d.year,
        p.product_name,
        p.revenue_stream,
        sum(f.amount) AS revenue
    FROM fact_actuals f
    JOIN dim_date d USING (date_key)
    JOIN dim_account a USING (account_key)
    JOIN dim_product p USING (product_key)
    WHERE a.account_category = 'Revenue'
    GROUP BY d.year, p.product_name, p.revenue_stream
)
SELECT *,
       revenue / sum(revenue) OVER (PARTITION BY year) AS revenue_mix_pct,
       revenue - lag(revenue) OVER (PARTITION BY product_name ORDER BY year) AS revenue_yoy_change
FROM product_revenue
ORDER BY year, revenue DESC;
