SELECT
    year,
    customer_id,
    customer_name,
    segment,
    region,
    sum(revenue) AS revenue,
    sum(cogs) AS cogs,
    sum(gross_profit) AS gross_profit,
    sum(gross_profit) / nullif(sum(revenue), 0) AS gross_margin_pct,
    sum(support_tickets) AS support_tickets,
    sum(implementation_hours) AS implementation_hours,
    dense_rank() OVER (PARTITION BY year ORDER BY sum(gross_profit) DESC) AS gross_profit_rank
FROM mart_customer_profitability
GROUP BY year, customer_id, customer_name, segment, region
ORDER BY year, gross_profit_rank;
