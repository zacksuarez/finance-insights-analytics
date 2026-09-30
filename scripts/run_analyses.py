"""Execute every analytical SQL file and materialize reviewer-friendly CSV outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def materialize_analyses(database_path: Path, output_dir: Path) -> dict[str, int]:
    database_path = database_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path), read_only=True)
    row_counts: dict[str, int] = {}
    try:
        for sql_path in sorted((PROJECT_ROOT / "sql" / "analysis").glob("*.sql")):
            query = sql_path.read_text(encoding="utf-8").strip().rstrip(";")
            output_path = output_dir / f"{sql_path.stem}.csv"
            escaped_path = output_path.as_posix().replace("'", "''")
            connection.execute(
                f"COPY ({query}) TO '{escaped_path}' (HEADER, DELIMITER ',')"
            )
            row_counts[sql_path.stem] = connection.execute(
                f"SELECT count(*) FROM ({query}) result"
            ).fetchone()[0]
    finally:
        connection.close()
    return row_counts


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
        default=PROJECT_ROOT / "data" / "curated" / "analysis",
    )
    args = parser.parse_args()
    counts = materialize_analyses(args.database, args.output_dir)
    for name, count in counts.items():
        print(f"{name}: {count:,} rows")


if __name__ == "__main__":
    main()
