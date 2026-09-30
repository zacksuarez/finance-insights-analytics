WITH annual AS (
    SELECT year, customer_id, customer_name, sum(revenue) AS revenue, sum(gross_profit) AS gross_profit,
           sum(gross_profit) / nullif(sum(revenue), 0) AS gross_margin_pct
    FROM mart_customer_profitability
    GROUP BY year, customer_id, customer_name
), compared AS (
    SELECT
        current.customer_id,
        current.customer_name,
        prior.gross_profit AS prior_year_gross_profit,
        current.gross_profit AS current_year_gross_profit,
        current.gross_profit - prior.gross_profit AS gross_profit_change,
        prior.gross_margin_pct AS prior_year_margin_pct,
        current.gross_margin_pct AS current_year_margin_pct,
        current.gross_margin_pct - prior.gross_margin_pct AS margin_change
    FROM annual current
    JOIN annual prior ON current.customer_id = prior.customer_id AND current.year = prior.year + 1
    WHERE current.year = 2025
)
SELECT *,
       dense_rank() OVER (ORDER BY gross_profit_change DESC) AS improvement_rank,
       dense_rank() OVER (ORDER BY gross_profit_change ASC) AS deterioration_rank
FROM compared
ORDER BY gross_profit_change DESC;
