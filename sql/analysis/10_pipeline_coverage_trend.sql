WITH company AS (
    SELECT
        period,
        sum(gross_pipeline) AS gross_pipeline,
        sum(weighted_pipeline) AS weighted_pipeline,
        sum(actual_revenue) AS actual_revenue,
        sum(weighted_pipeline) / nullif(sum(actual_revenue), 0) AS weighted_pipeline_coverage
    FROM mart_pipeline_coverage
    GROUP BY period
)
SELECT *,
       avg(weighted_pipeline_coverage) OVER (
           ORDER BY period ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
       ) AS rolling_3m_coverage,
       weighted_pipeline_coverage - lag(weighted_pipeline_coverage, 3) OVER (ORDER BY period) AS change_vs_3m_prior
FROM company
ORDER BY period;
