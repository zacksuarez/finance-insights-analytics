from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import duckdb

from scripts.build_model import build_model
from scripts.generate_data import SEED, generate_dataset
from scripts.run_analyses import materialize_analyses


class V1DataFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp_directory.name)
        cls.raw = cls.root / "raw"
        cls.database = cls.root / "curated" / "test.duckdb"
        cls.analysis = cls.root / "analysis"
        cls.manifest = generate_dataset(cls.raw)
        cls.counts = build_model(cls.raw, cls.database)
        cls.connection = duckdb.connect(str(cls.database), read_only=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()
        cls.temp_directory.cleanup()

    def test_generation_is_reproducible(self) -> None:
        second_raw = self.root / "raw_second"
        second_manifest = generate_dataset(second_raw, SEED)
        self.assertEqual(self.manifest["sha256"], second_manifest["sha256"])
        self.assertEqual(self.manifest["row_counts"], second_manifest["row_counts"])

    def test_source_volumes_are_in_expected_ranges(self) -> None:
        counts = self.manifest["row_counts"]
        self.assertEqual(counts["crm_customers.csv"], 150)
        self.assertGreater(counts["erp_transactions.csv"], 25_000)
        self.assertEqual(counts["epm_plan.csv"], counts["erp_transactions.csv"] * 2)
        self.assertEqual(counts["sales_pipeline.csv"], 24 * 32)
        self.assertGreater(counts["operational_kpis.csv"], 3_000)

    def test_manifest_records_fixed_seed_and_period(self) -> None:
        self.assertEqual(self.manifest["seed"], SEED)
        self.assertEqual(self.manifest["period_start"], "2024-01")
        self.assertEqual(self.manifest["period_end"], "2025-12")

    def test_all_data_quality_checks_pass(self) -> None:
        failures = self.connection.execute(
            "SELECT check_name, failure_count FROM dq_results WHERE failure_count <> 0"
        ).fetchall()
        self.assertEqual(failures, [])

    def test_source_fact_and_mart_totals_reconcile(self) -> None:
        rows = self.connection.execute(
            "SELECT measure, source_total, fact_total, mart_total FROM mart_reconciliation"
        ).fetchall()
        self.assertEqual(len(rows), 3)
        for measure, source, fact, mart in rows:
            with self.subTest(measure=measure):
                self.assertAlmostEqual(float(source), float(fact), places=2)
                self.assertAlmostEqual(float(fact), float(mart), places=2)

    def test_dimension_and_fact_keys_are_unique(self) -> None:
        key_checks = (
            ("dim_customer", "customer_key"),
            ("dim_product", "product_key"),
            ("dim_department", "department_key"),
            ("dim_account", "account_key"),
            ("fact_actuals", "transaction_id"),
            ("fact_plan", "plan_key"),
            ("fact_pipeline", "opportunity_id"),
            ("fact_operational_kpi", "kpi_key"),
        )
        for table, key in key_checks:
            with self.subTest(table=table):
                total, distinct = self.connection.execute(
                    f"SELECT count(*), count(DISTINCT {key}) FROM {table}"
                ).fetchone()
                self.assertEqual(total, distinct)

    def test_revenue_growth_and_margin_pressure_story_exists(self) -> None:
        results = self.connection.execute(
            """
            SELECT year, sum(revenue), sum(gross_profit) / sum(revenue)
            FROM mart_customer_profitability
            GROUP BY year ORDER BY year
            """
        ).fetchall()
        _, revenue_2024, margin_2024 = results[0]
        _, revenue_2025, margin_2025 = results[1]
        self.assertGreater(float(revenue_2025) / float(revenue_2024) - 1, 0.10)
        self.assertLess(float(margin_2025), float(margin_2024) - 0.03)

    def test_designated_customer_grows_while_profitability_deteriorates(self) -> None:
        results = self.connection.execute(
            """
            SELECT year, sum(revenue), sum(gross_profit) / sum(revenue)
            FROM mart_customer_profitability
            WHERE customer_id = 'CUST001'
            GROUP BY year ORDER BY year
            """
        ).fetchall()
        _, revenue_2024, margin_2024 = results[0]
        _, revenue_2025, margin_2025 = results[1]
        self.assertGreater(float(revenue_2025), float(revenue_2024))
        self.assertLess(float(margin_2025), float(margin_2024) - 0.08)

    def test_west_forecast_accuracy_worsens(self) -> None:
        early_west, late_west, late_other = self.connection.execute(
            """
            SELECT
                avg(CASE WHEN region = 'West' AND period BETWEEN '2025-01' AND '2025-03' THEN absolute_forecast_error_pct END),
                avg(CASE WHEN region = 'West' AND period BETWEEN '2025-10' AND '2025-12' THEN absolute_forecast_error_pct END),
                avg(CASE WHEN region <> 'West' AND period BETWEEN '2025-10' AND '2025-12' THEN absolute_forecast_error_pct END)
            FROM mart_regional_performance
            """
        ).fetchone()
        self.assertGreater(float(late_west), float(early_west) * 2)
        self.assertGreater(float(late_west), float(late_other) * 5)

    def test_pipeline_coverage_declines(self) -> None:
        early, late = self.connection.execute(
            """
            WITH company AS (
                SELECT period, sum(weighted_pipeline) / sum(actual_revenue) AS coverage
                FROM mart_pipeline_coverage GROUP BY period
            )
            SELECT
                avg(CASE WHEN period BETWEEN '2024-01' AND '2024-03' THEN coverage END),
                avg(CASE WHEN period BETWEEN '2025-10' AND '2025-12' THEN coverage END)
            FROM company
            """
        ).fetchone()
        self.assertLess(float(late), float(early) * 0.60)

    def test_pipeline_warning_precedes_revenue_growth_slowdown(self) -> None:
        early_growth, late_growth = self.connection.execute(
            """
            WITH monthly AS (
                SELECT period, revenue,
                       lag(revenue, 12) OVER (ORDER BY period) AS prior_year_revenue
                FROM mart_monthly_pnl
            )
            SELECT
                avg(CASE WHEN period BETWEEN '2025-01' AND '2025-06' THEN revenue / prior_year_revenue - 1 END),
                avg(CASE WHEN period BETWEEN '2025-10' AND '2025-12' THEN revenue / prior_year_revenue - 1 END)
            FROM monthly
            """
        ).fetchone()
        self.assertGreater(float(early_growth), 0.14)
        self.assertLess(float(late_growth), 0.10)

    def test_engineering_software_overrun_is_structural(self) -> None:
        periods, unfavorable_periods = self.connection.execute(
            """
            SELECT count(*), count(*) FILTER (WHERE forecast_variance < 0)
            FROM mart_department_opex
            WHERE department_name = 'Engineering' AND account_name = 'Software'
            """
        ).fetchone()
        self.assertEqual(periods, 24)
        self.assertEqual(unfavorable_periods, 24)

    def test_customer_concentration_is_meaningful_but_plausible(self) -> None:
        top_five_share = self.connection.execute(
            """
            WITH annual AS (
                SELECT customer_id, sum(revenue) AS revenue
                FROM mart_customer_profitability WHERE year = 2025 GROUP BY customer_id
            ), ranked AS (
                SELECT revenue, row_number() OVER (ORDER BY revenue DESC) AS rank,
                       revenue / sum(revenue) OVER () AS share
                FROM annual
            )
            SELECT sum(share) FROM ranked WHERE rank <= 5
            """
        ).fetchone()[0]
        self.assertGreater(float(top_five_share), 0.18)
        self.assertLess(float(top_five_share), 0.50)

    def test_all_required_analyses_execute_and_materialize(self) -> None:
        counts = materialize_analyses(self.database, self.analysis)
        self.assertEqual(len(counts), 14)
        self.assertTrue(all(count > 0 for count in counts.values()))
        for output in self.analysis.glob("*.csv"):
            with output.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle))
            self.assertGreater(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
