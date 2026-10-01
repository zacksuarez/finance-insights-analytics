"""Materialize selective V2 executive analytics as CSV and Parquet."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = {
    "executive_kpis": "mart_executive_kpis",
    "customer_profitability": "mart_customer_profitability_v2",
    "customer_concentration": "mart_customer_concentration_v2",
    "margin_analysis": "mart_margin_analysis",
    "forecast_accuracy": "mart_forecast_accuracy_v2",
    "pipeline_analysis": "mart_pipeline_analysis_v2",
    "opex_management": "mart_opex_management_v2",
    "regional_performance": "mart_regional_performance_v2",
    "management_issue_register": "mart_management_issue_register",
    "scenario_analysis": "mart_scenario_analysis",
}


def materialize_v2_outputs(database_path: Path, output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path.resolve()), read_only=True)
    counts: dict[str, int] = {}
    try:
        for output_name, relation_name in OUTPUTS.items():
            counts[output_name] = connection.execute(
                f"SELECT count(*) FROM {relation_name}"
            ).fetchone()[0]
            for extension, copy_options in (
                ("csv", "FORMAT CSV, HEADER"),
                ("parquet", "FORMAT PARQUET, COMPRESSION ZSTD"),
            ):
                path = (output_dir / f"{output_name}.{extension}").resolve().as_posix().replace("'", "''")
                connection.execute(
                    f"COPY (SELECT * FROM {relation_name}) TO '{path}' ({copy_options})"
                )
    finally:
        connection.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "curated" / "finance_analytics.duckdb",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "curated" / "v2",
    )
    args = parser.parse_args()
    counts = materialize_v2_outputs(args.database, args.output_dir)
    for name, count in counts.items():
        print(f"{name}: {count:,} rows (CSV + Parquet)")


if __name__ == "__main__":
    main()
