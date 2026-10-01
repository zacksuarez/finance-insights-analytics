"""Run deterministic V3 schema and business-guardrail evaluations without API calls."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from finance_ai.evaluation import run_evaluations
from finance_ai.evidence import build_evidence_package


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT_ROOT / "data" / "curated" / "finance_analytics.duckdb")
    args = parser.parse_args()
    results = run_evaluations(build_evidence_package(args.database))
    for result in results:
        print(f"{'PASS' if result['passed'] else 'FAIL'}  {result['name']}: {result['detail']}")
    failures = [item for item in results if not item["passed"]]
    if failures:
        raise SystemExit(f"{len(failures)} AI evaluation case(s) failed")


if __name__ == "__main__":
    main()
