"""Build and validate the local DuckDB analytical model."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_SEQUENCE = (
    "sql/staging/00_staging.sql",
    "sql/marts/10_dimensions.sql",
    "sql/marts/20_facts.sql",
    "sql/marts/30_finance_marts.sql",
    "sql/config/management_thresholds.sql",
    "sql/marts/40_v2_executive_marts.sql",
    "sql/quality/quality_checks.sql",
    "sql/quality/50_v2_quality_checks.sql",
)


def execute_sql_file(connection: duckdb.DuckDBPyConnection, path: Path, raw_dir: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    sql = sql.replace("${RAW_PATH}", raw_dir.resolve().as_posix().replace("'", "''"))
    connection.execute(sql)


def build_model(raw_dir: Path, database_path: Path) -> dict[str, int]:
    raw_dir = raw_dir.resolve()
    database_path = database_path.resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {raw_dir}")

    build_path = database_path.with_name(database_path.name + ".building")
    build_path.unlink(missing_ok=True)
    connection = duckdb.connect(str(build_path))
    try:
        for relative_path in SQL_SEQUENCE:
            execute_sql_file(connection, PROJECT_ROOT / relative_path, raw_dir)

        failures = connection.execute(
            """
            SELECT check_name, failure_count FROM dq_results WHERE failure_count <> 0
            UNION ALL
            SELECT check_name, failure_count FROM dq_v2_results WHERE failure_count <> 0
            """
        ).fetchall()
        if failures:
            details = ", ".join(f"{name}={count}" for name, count in failures)
            raise RuntimeError(f"Data-quality checks failed: {details}")

        counts = {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in (
                "dim_date",
                "dim_customer",
                "dim_product",
                "dim_department",
                "dim_account",
                "fact_actuals",
                "fact_plan",
                "fact_pipeline",
                "fact_operational_kpi",
                "mart_finance_monthly",
                "mart_executive_kpis",
                "mart_customer_profitability_v2",
                "mart_customer_concentration_v2",
                "mart_margin_analysis",
                "mart_forecast_accuracy_v2",
                "mart_pipeline_analysis_v2",
                "mart_opex_management_v2",
                "mart_regional_performance_v2",
                "mart_management_issue_register",
                "mart_scenario_analysis",
            )
        }
        connection.execute("CHECKPOINT")
    except Exception:
        connection.close()
        build_path.unlink(missing_ok=True)
        raise
    connection.close()
    build_path.replace(database_path)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=PROJECT_ROOT / "data" / "raw")
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "curated" / "finance_analytics.duckdb",
    )
    args = parser.parse_args()
    counts = build_model(args.raw_dir, args.database)
    for table, count in counts.items():
        print(f"{table}: {count:,}")
    print(f"Built {args.database.resolve()}")


if __name__ == "__main__":
    main()
