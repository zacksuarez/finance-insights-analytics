"""Build the deterministic verified evidence package consumed by V3 AI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from finance_ai.evidence import build_evidence_package


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT_ROOT / "data" / "curated" / "finance_analytics.duckdb")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "outputs" / "verified-ai-context.json")
    args = parser.parse_args()
    package = build_evidence_package(args.database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(package.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Period: {package.period}")
    print(f"Priority issues: {len(package.priority_issues)}")
    print(f"Evidence items: {len(package.evidence)}")
    print(f"Trusted data gate: {'PASS' if package.data_quality_status.passed and package.reconciliation_status.passed else 'FAIL'}")
    print(f"Generated {args.output.resolve()}")


if __name__ == "__main__":
    main()
