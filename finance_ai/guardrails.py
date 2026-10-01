"""Semantic validation for structured AI executive insights."""

from __future__ import annotations

import re

from finance_ai.models import EvidencePackage, ExecutiveInsightOutput


PRIORITY_RANK = {"low": 1, "medium": 2, "high": 3}
NUMERIC_CLAIM = re.compile(r"(?<![A-Za-z_-])[-+]?\d+(?:[.,]\d+)?%?")
CAUSAL_CLAIM = re.compile(
    r"\b(caused|causes|causing|because of|due to|led to|resulted in|driven by|responsible for)\b",
    re.IGNORECASE,
)


class GuardrailViolation(ValueError):
    def __init__(self, violations: list[str]) -> None:
        super().__init__("; ".join(violations))
        self.violations = violations


def _prose(output: ExecutiveInsightOutput) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = [("executive_summary", output.executive_summary)]
    for insight in output.top_insights:
        prefix = f"top_insights.{insight.insight_id}"
        values.extend([
            (f"{prefix}.title", insight.title),
            (f"{prefix}.summary", insight.summary),
            (f"{prefix}.business_implication", insight.business_implication),
        ])
        values.extend((f"{prefix}.recommended_follow_up", item) for item in insight.recommended_follow_up)
    values.extend(("unresolved_questions", item) for item in output.unresolved_questions)
    values.extend(("recommended_actions", item) for item in output.recommended_actions)
    values.extend(("confidence_notes", item) for item in output.confidence_notes)
    return values


def validate_ai_output(context: EvidencePackage, output: ExecutiveInsightOutput) -> None:
    issue_map = {item.issue_id: item for item in context.priority_issues}
    evidence_ids = {item.evidence_id for item in context.evidence}
    entity_ids = {item.entity_id for item in context.entity_catalog}
    violations: list[str] = []

    insight_ids = [item.insight_id for item in output.top_insights]
    if len(insight_ids) != len(set(insight_ids)):
        violations.append("duplicate insight ID")

    for insight in output.top_insights:
        unknown_issues = sorted(set(insight.issue_ids) - issue_map.keys())
        unknown_evidence = sorted(set(insight.evidence_ids) - evidence_ids)
        unknown_entities = sorted(set(insight.entity_ids) - entity_ids)
        if unknown_issues:
            violations.append(f"{insight.insight_id}: unknown issue IDs {unknown_issues}")
        if unknown_evidence:
            violations.append(f"{insight.insight_id}: unknown evidence IDs {unknown_evidence}")
        if unknown_entities:
            violations.append(f"{insight.insight_id}: unknown entity IDs {unknown_entities}")

        known_issues = [issue_map[item] for item in insight.issue_ids if item in issue_map]
        if known_issues:
            required_priority = max(
                PRIORITY_RANK[item.minimum_priority] for item in known_issues
            )
            if PRIORITY_RANK[insight.priority] < required_priority:
                violations.append(f"{insight.insight_id}: priority downgrades deterministic severity")
            if insight.priority == "high" and not any(item.severity == "High" for item in known_issues):
                violations.append(f"{insight.insight_id}: non-high issues presented as high priority")

    unknown_known_facts = sorted(set(output.known_facts) - evidence_ids)
    if unknown_known_facts:
        violations.append(f"knownFacts contains unknown evidence IDs {unknown_known_facts}")

    for location, text in _prose(output):
        if NUMERIC_CLAIM.search(text):
            violations.append(f"{location}: numeric claim must be rendered from deterministic evidence")
        if CAUSAL_CLAIM.search(text):
            violations.append(f"{location}: unsupported causal language")

    if not context.priority_issues and output.top_insights:
        violations.append("top insights supplied when no deterministic priority issues exist")
    if violations:
        raise GuardrailViolation(violations)
