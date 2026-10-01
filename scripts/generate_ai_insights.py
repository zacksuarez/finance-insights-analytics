"""Explicitly generate and validate one AI-assisted executive insight artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from finance_ai.config import AIConfig
from finance_ai.evidence import build_evidence_package
from finance_ai.presentation import render_markdown
from finance_ai.providers.openai_provider import OpenAIInsightProvider
from finance_ai.service import ExecutiveInsightService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT_ROOT / "data" / "curated" / "finance_analytics.duckdb")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "outputs" / "ai-executive-insights.md")
    args = parser.parse_args()
    context = build_evidence_package(args.database)
    config = AIConfig.from_environment()
    if config.provider != "openai":
        raise SystemExit(f"Unsupported AI_PROVIDER: {config.provider}")
    output = ExecutiveInsightService(OpenAIInsightProvider(config)).generate(context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(context, output), encoding="utf-8")
    print(f"Validated {len(output.top_insights)} executive insights")
    print(f"Generated {args.output.resolve()}")


if __name__ == "__main__":
    main()
