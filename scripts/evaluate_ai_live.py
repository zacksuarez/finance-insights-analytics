"""Opt-in single-call live AI evaluation using the current verified package."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from finance_ai.config import AIConfig
from finance_ai.evidence import build_evidence_package
from finance_ai.providers.openai_provider import OpenAIInsightProvider
from finance_ai.service import ExecutiveInsightService


def main() -> None:
    context = build_evidence_package(PROJECT_ROOT / "data" / "curated" / "finance_analytics.duckdb")
    config = AIConfig.from_environment()
    result = ExecutiveInsightService(OpenAIInsightProvider(config)).generate(context)
    print("PASS  live structured output and business guardrails")
    print(f"Validated insights: {len(result.top_insights)}")


if __name__ == "__main__":
    main()
