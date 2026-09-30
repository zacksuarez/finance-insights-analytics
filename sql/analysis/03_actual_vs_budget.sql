SELECT
    d.period,
    a.financial_statement_line,
    sum(f.actual_amount) AS actual_amount,
    sum(f.budget_amount) AS budget_amount,
    sum(f.actual_amount - f.budget_amount) AS variance_amount,
    CASE WHEN sum(abs(f.budget_amount)) = 0 THEN NULL
         ELSE sum(f.actual_amount - f.budget_amount) / sum(abs(f.budget_amount)) END AS variance_pct
FROM mart_finance_monthly f
JOIN dim_date d USING (date_key)
JOIN dim_account a USING (account_key)
GROUP BY d.period, a.financial_statement_line
ORDER BY d.period, min(a.display_order);
