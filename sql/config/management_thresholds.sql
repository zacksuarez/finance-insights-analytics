CREATE OR REPLACE TABLE config_management_thresholds AS
SELECT * FROM (
    VALUES
        ('revenue_variance_material_pct', 0.05, 'ratio', 'Material company revenue variance versus plan.'),
        ('margin_deterioration_bps', 200.0, 'basis_points', 'Material year-over-year gross-margin deterioration.'),
        ('forecast_accuracy_min', 0.85, 'ratio', 'Minimum acceptable deterministic forecast accuracy.'),
        ('pipeline_coverage_min', 0.75, 'ratio', 'Minimum weighted pipeline coverage against forecast revenue.'),
        ('customer_top10_concentration_max', 0.25, 'ratio', 'Maximum preferred share of revenue from the top ten customers.'),
        ('customer_margin_deterioration_bps', 500.0, 'basis_points', 'Material annual customer margin deterioration.'),
        ('customer_low_growth_pct', 0.05, 'ratio', 'Annual customer growth below this level is considered low.'),
        ('opex_variance_material_pct', 0.05, 'ratio', 'Material monthly OpEx variance percentage.'),
        ('opex_variance_material_amount', 10000.0, 'currency', 'Material monthly OpEx variance amount.'),
        ('opex_persistence_months', 4.0, 'months_in_trailing_6', 'Material unfavorable months required for a structural overrun.')
) thresholds(threshold_name, threshold_value, threshold_unit, description);

CREATE OR REPLACE TABLE config_scenario_assumptions AS
SELECT * FROM (
    VALUES
        ('Base', 0.05, 0.0, 0.04, 1),
        ('Upside', 0.10, 150.0, 0.03, 2),
        ('Downside', -0.02, -200.0, 0.06, 3)
) scenarios(scenario_name, revenue_growth_adjustment, gross_margin_adjustment_bps, opex_growth_adjustment, display_order);
