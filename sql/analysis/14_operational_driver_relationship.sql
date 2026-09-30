SELECT
    year,
    customer_id,
    customer_name,
    segment,
    region,
    sum(revenue) AS revenue,
    sum(gross_profit) AS gross_profit,
    sum(gross_profit) / nullif(sum(revenue), 0) AS gross_margin_pct,
    sum(active_users) AS active_users,
    sum(support_tickets) AS support_tickets,
    sum(implementation_hours) AS implementation_hours,
    sum(support_tickets) / nullif(sum(revenue) / 1000000, 0) AS tickets_per_million_revenue,
    sum(implementation_hours) / nullif(sum(revenue) / 1000000, 0) AS implementation_hours_per_million_revenue
FROM mart_customer_profitability
GROUP BY year, customer_id, customer_name, segment, region
ORDER BY year, gross_margin_pct;
