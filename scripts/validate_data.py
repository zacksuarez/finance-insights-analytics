"""Run deterministic data-quality and reconciliation checks against the V1 model."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def validate(database_path: Path) -> None:
    connection = duckdb.connect(str(database_path.resolve()), read_only=True)
    try:
        checks = connection.execute(
            "SELECT check_name, failure_count FROM dq_results ORDER BY check_name"
        ).fetchall()
        reconciliation = connection.execute(
            "SELECT measure, source_total, fact_total, mart_total FROM mart_reconciliation ORDER BY measure"
        ).fetchall()
    finally:
        connection.close()

    for name, failures in checks:
        print(f"{'PASS' if failures == 0 else 'FAIL'}  {name}: {failures}")
    print("\nReconciliation")
    for measure, source, fact, mart in reconciliation:
        print(f"{measure:8} source={source:.2f} fact={fact:.2f} mart={mart:.2f}")

    failed = [(name, failures) for name, failures in checks if failures]
    if failed:
        raise SystemExit(f"Validation failed: {failed}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "curated" / "finance_analytics.duckdb",
    )
    args = parser.parse_args()
    validate(args.database)


if __name__ == "__main__":
    main()
