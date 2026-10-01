from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import duckdb

from scripts.build_model import build_model
from scripts.build_v2_outputs import OUTPUTS, materialize_v2_outputs
from scripts.generate_data import generate_dataset
from scripts.generate_insight_pack import generate_insight_pack


class V2ExecutiveAnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp_directory.name)
        cls.raw = cls.root / "raw"
        cls.database = cls.root / "curated" / "test.duckdb"
        cls.outputs = cls.root / "v2"
        cls.pack = cls.root / "management-insight-pack.md"
        generate_dataset(cls.raw)
        build_model(cls.raw, cls.database)
        cls.connection = duckdb.connect(str(cls.database), read_only=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()
        cls.temp_directory.cleanup()

    def test_executive_kpis_reconcile_and_have_unique_months(self) -> None:
        total, distinct_periods = self.connection.execute(
            "SELECT count(*), count(DISTINCT period) FROM mart_executive_kpis"
        ).fetchone()
        self.assertEqual(total, 24)
        self.assertEqual(total, distinct_periods)
        failures = self.connection.execute(
            """
            SELECT count(*) FROM mart_executive_kpis k
            JOIN mart_monthly_pnl p USING (period)
            WHERE abs(k.revenue - p.revenue) > 0.01
               OR abs(k.gross_profit - p.gross_profit) > 0.01
               OR abs(k.operating_contribution - p.operating_contribution) > 0.01
            """
        ).fetchone()[0]
        self.assertEqual(failures, 0)

    def test_gross_margin_and_yoy_basis_points_are_correct(self) -> None:
        failures = self.connection.execute(
            """
            WITH expected AS (
                SELECT period, gross_profit / revenue AS expected_margin,
                       (gross_profit / revenue - lag(gross_profit / revenue, 12) OVER (ORDER BY period)) * 10000 AS expected_bps
                FROM mart_executive_kpis
            )
            SELECT count(*) FROM mart_executive_kpis k JOIN expected e USING (period)
            WHERE abs(k.gross_margin_pct - e.expected_margin) > 0.000001
               OR abs(k.gross_margin_yoy_bps - e.expected_bps) > 0.01
            """
        ).fetchone()[0]
        self.assertEqual(failures, 0)

    def test_customer_profitability_reconciles_to_company(self) -> None:
        failures = self.connection.execute(
            """
            WITH customer AS (
                SELECT year, sum(revenue) AS revenue, sum(gross_profit) AS gross_profit
                FROM mart_customer_profitability_v2 GROUP BY year
            ), company AS (
                SELECT year, sum(revenue) AS revenue, sum(gross_profit) AS gross_profit
                FROM mart_executive_kpis GROUP BY year
            )
            SELECT count(*) FROM customer c JOIN company k USING (year)
            WHERE abs(c.revenue - k.revenue) > 0.01 OR abs(c.gross_profit - k.gross_profit) > 0.01
            """
        ).fetchone()[0]
        self.assertEqual(failures, 0)

    def test_customer_concentration_metrics_match_ranked_customer_data(self) -> None:
        period = self.connection.execute(
            "SELECT max(period) FROM mart_customer_concentration_v2"
        ).fetchone()[0]
        expected = self.connection.execute(
            """
            WITH ranked AS (
                SELECT revenue,
                       row_number() OVER (ORDER BY revenue DESC) AS revenue_rank,
                       revenue / sum(revenue) OVER () AS revenue_share
                FROM mart_customer_profitability WHERE period = ?
            )
            SELECT
                max(CASE WHEN revenue_rank = 1 THEN revenue_share END),
                sum(CASE WHEN revenue_rank <= 5 THEN revenue_share ELSE 0 END),
                sum(CASE WHEN revenue_rank <= 10 THEN revenue_share ELSE 0 END),
                sum(revenue_share * revenue_share) * 10000
            FROM ranked
            """,
            [period],
        ).fetchone()
        actual = self.connection.execute(
            """
            SELECT top_1_revenue_pct, top_5_revenue_pct, top_10_revenue_pct, hhi
            FROM mart_customer_concentration_v2 WHERE period = ?
            """,
            [period],
        ).fetchone()
        for expected_value, actual_value in zip(expected, actual):
            self.assertAlmostEqual(float(expected_value), float(actual_value), places=8)

    def test_forecast_accuracy_formula_and_west_deterioration(self) -> None:
        failures = self.connection.execute(
            """
            SELECT count(*) FROM mart_forecast_accuracy_v2
            WHERE abs(forecast_accuracy_pct - greatest(0, 1 - absolute_forecast_error_pct)) > 0.000001
            """
        ).fetchone()[0]
        self.assertEqual(failures, 0)
        early, late = self.connection.execute(
            """
            SELECT
                avg(CASE WHEN period BETWEEN '2025-01' AND '2025-03' THEN forecast_accuracy_pct END),
                avg(CASE WHEN period BETWEEN '2025-10' AND '2025-12' THEN forecast_accuracy_pct END)
            FROM mart_forecast_accuracy_v2
            WHERE entity_type = 'Region' AND entity_name = 'West'
            """
        ).fetchone()
        self.assertLess(float(late), float(early) - 0.10)

    def test_pipeline_coverage_uses_weighted_pipeline_and_forecast_revenue(self) -> None:
        failures = self.connection.execute(
            """
            SELECT count(*) FROM mart_pipeline_analysis_v2
            WHERE abs(weighted_pipeline_coverage - regional_weighted_pipeline / revenue_requirement) > 0.000001
            """
        ).fetchone()[0]
        self.assertEqual(failures, 0)
        early, late = self.connection.execute(
            """
            SELECT
                avg(CASE WHEN period BETWEEN '2025-01' AND '2025-03' THEN pipeline_coverage END),
                avg(CASE WHEN period BETWEEN '2025-10' AND '2025-12' THEN pipeline_coverage END)
            FROM mart_executive_kpis
            """
        ).fetchone()
        self.assertLess(float(late), float(early) * 0.70)

    def test_structural_opex_classification_surfaces_engineering_software(self) -> None:
        result = self.connection.execute(
            """
            SELECT variance_classification, material_unfavorable_months_trailing_6
            FROM mart_opex_management_v2
            WHERE period = (SELECT max(period) FROM mart_opex_management_v2)
              AND department_name = 'Engineering' AND account_name = 'Software'
            """
        ).fetchone()
        self.assertEqual(result[0], "Structural Overrun")
        self.assertEqual(result[1], 6)

    def test_issue_register_contains_each_expected_rule_type(self) -> None:
        expected_types = {
            "Margin Deterioration",
            "Forecast Accuracy Deterioration",
            "Pipeline Coverage Weakness",
            "Structural OpEx Overrun",
            "Customer Profitability Deterioration",
            "Customer Concentration Risk",
        }
        actual_types = {
            row[0]
            for row in self.connection.execute(
                "SELECT DISTINCT issue_type FROM mart_management_issue_register"
            ).fetchall()
        }
        self.assertEqual(actual_types, expected_types)
        self.assertEqual(
            self.connection.execute(
                "SELECT count(*) - count(DISTINCT issue_id) FROM mart_management_issue_register"
            ).fetchone()[0],
            0,
        )

    def test_scenario_mathematics_and_ordering(self) -> None:
        failures = self.connection.execute(
            """
            SELECT count(*) FROM mart_scenario_analysis
            WHERE abs(scenario_gross_profit - scenario_revenue * scenario_gross_margin_pct) > 0.01
               OR abs(scenario_operating_contribution - scenario_gross_profit - scenario_operating_expense) > 0.01
            """
        ).fetchone()[0]
        self.assertEqual(failures, 0)
        scenarios = dict(
            self.connection.execute(
                "SELECT scenario_name, scenario_operating_contribution FROM mart_scenario_analysis"
            ).fetchall()
        )
        self.assertGreater(scenarios["Upside"], scenarios["Base"])
        self.assertGreater(scenarios["Base"], scenarios["Downside"])

    def test_margin_bridge_reconciles_for_each_dimension(self) -> None:
        company_change = self.connection.execute(
            """
            WITH annual AS (
                SELECT year, sum(gross_profit) / sum(revenue) AS margin
                FROM mart_customer_profitability_v2 GROUP BY year
            )
            SELECT (max(CASE WHEN year = 2025 THEN margin END)
                  - max(CASE WHEN year = 2024 THEN margin END)) * 10000
            FROM annual
            """
        ).fetchone()[0]
        bridges = self.connection.execute(
            """
            SELECT dimension_type, sum(mix_effect_bps + margin_rate_effect_bps)
            FROM mart_margin_analysis WHERE year = 2025 GROUP BY dimension_type
            """
        ).fetchall()
        self.assertEqual(len(bridges), 3)
        for dimension_type, bridge_change in bridges:
            with self.subTest(dimension_type=dimension_type):
                self.assertAlmostEqual(float(bridge_change), float(company_change), places=4)

    def test_regional_totals_reconcile_and_rank(self) -> None:
        failures = self.connection.execute(
            """
            WITH regional AS (
                SELECT period, sum(revenue) AS revenue, count(DISTINCT revenue_rank) AS ranks
                FROM mart_regional_performance_v2 GROUP BY period
            )
            SELECT count(*) FROM regional r JOIN mart_executive_kpis k USING (period)
            WHERE abs(r.revenue - k.revenue) > 0.01 OR r.ranks <> 3
            """
        ).fetchone()[0]
        self.assertEqual(failures, 0)

    def test_v1_business_stories_surface_in_v2_outputs(self) -> None:
        revenue_growth, margin_change = self.connection.execute(
            """
            WITH annual AS (
                SELECT year, sum(revenue) AS revenue, sum(gross_profit) / sum(revenue) AS margin
                FROM mart_executive_kpis GROUP BY year
            )
            SELECT current.revenue / prior.revenue - 1, current.margin - prior.margin
            FROM annual current JOIN annual prior ON current.year = prior.year + 1
            WHERE current.year = 2025
            """
        ).fetchone()
        self.assertGreater(float(revenue_growth), 0.10)
        self.assertLess(float(margin_change), -0.03)
        northstar = self.connection.execute(
            """
            SELECT profitability_trend, margin_change_bps
            FROM mart_customer_profitability_v2 WHERE year = 2025 AND customer_id = 'CUST001'
            """
        ).fetchone()
        self.assertEqual(northstar[0], "Deteriorating")
        self.assertLess(float(northstar[1]), -1000)

    def test_executive_mart_grains_have_no_duplicates(self) -> None:
        grain_checks = {
            "mart_executive_kpis": "period",
            "mart_customer_profitability_v2": "year, customer_id",
            "mart_customer_concentration_v2": "period",
            "mart_margin_analysis": "year, dimension_type, member_name",
            "mart_forecast_accuracy_v2": "period, entity_type, entity_name",
            "mart_pipeline_analysis_v2": "period, region, stage",
            "mart_opex_management_v2": "period, department_name, account_name",
            "mart_regional_performance_v2": "period, region",
            "mart_scenario_analysis": "scenario_name",
        }
        for table, grain in grain_checks.items():
            with self.subTest(table=table):
                duplicates = self.connection.execute(
                    f"SELECT count(*) FROM (SELECT {grain} FROM {table} GROUP BY ALL HAVING count(*) > 1) d"
                ).fetchone()[0]
                self.assertEqual(duplicates, 0)

    def test_v2_exports_and_management_pack_are_generated(self) -> None:
        counts = materialize_v2_outputs(self.database, self.outputs)
        self.assertEqual(set(counts), set(OUTPUTS))
        self.assertTrue(all(count > 0 for count in counts.values()))
        for output_name in OUTPUTS:
            self.assertGreater((self.outputs / f"{output_name}.csv").stat().st_size, 0)
            self.assertGreater((self.outputs / f"{output_name}.parquet").stat().st_size, 0)
        generate_insight_pack(self.database, self.pack)
        text = self.pack.read_text(encoding="utf-8")
        self.assertIn("## Executive KPI Snapshot", text)
        self.assertIn("## Management Issues", text)
        self.assertIn("Northstar Systems", text)
        self.assertNotIn("business-scenarios", text)

    def test_thresholds_are_centralized_and_complete(self) -> None:
        thresholds = {
            row[0]
            for row in self.connection.execute(
                "SELECT threshold_name FROM config_management_thresholds"
            ).fetchall()
        }
        self.assertEqual(len(thresholds), 10)
        self.assertIn("forecast_accuracy_min", thresholds)
        self.assertIn("opex_persistence_months", thresholds)


if __name__ == "__main__":
    unittest.main()
