"""Resolve AI references to deterministic evidence for human presentation."""

from __future__ import annotations

from finance_ai.models import EvidencePackage, ExecutiveInsightOutput


def presentation_payload(context: EvidencePackage, output: ExecutiveInsightOutput | None = None) -> dict[str, object]:
    evidence_map = {item.evidence_id: item.model_dump(mode="json") for item in context.evidence}
    issue_map = {item.issue_id: item.model_dump(mode="json") for item in context.priority_issues}
    payload: dict[str, object] = {
        "period": context.period,
        "trustStatus": {
            "trusted": context.data_quality_status.passed and context.reconciliation_status.passed,
            "dataQuality": context.data_quality_status.model_dump(mode="json"),
            "reconciliation": context.reconciliation_status.model_dump(mode="json"),
        },
        "executiveKpis": [evidence_map[item] for item in context.executive_kpis],
        "priorityIssues": [item.model_dump(mode="json") for item in context.priority_issues],
        "developerView": context.model_dump(mode="json"),
    }
    if output is not None:
        resolved_insights = []
        for insight in output.top_insights:
            item = insight.model_dump(mode="json")
            item["evidence"] = [evidence_map[evidence_id] for evidence_id in insight.evidence_ids]
            item["issues"] = [issue_map[issue_id] for issue_id in insight.issue_ids]
            resolved_insights.append(item)
        payload["aiInsights"] = {
            **output.model_dump(mode="json"),
            "top_insights": resolved_insights,
            "known_facts": [evidence_map[item] for item in output.known_facts],
        }
    return payload


def render_markdown(context: EvidencePackage, output: ExecutiveInsightOutput) -> str:
    evidence_map = {item.evidence_id: item for item in context.evidence}
    lines = [
        "# AI-Assisted Executive Insights",
        "",
        "Generated from synthetic portfolio data and verified deterministic analytics.",
        "",
        f"Period: `{context.period}`",
        "",
        "## Executive Summary",
        "",
        output.executive_summary,
        "",
        "## Top Insights",
    ]
    for insight in output.top_insights:
        lines.extend([
            "",
            f"### {insight.title}",
            "",
            f"Priority: **{insight.priority.title()}**",
            "",
            insight.summary,
            "",
            f"Business implication: {insight.business_implication}",
            "",
            "Evidence:",
        ])
        for evidence_id in insight.evidence_ids:
            item = evidence_map[evidence_id]
            lines.append(f"- `{evidence_id}`: {item.metric} = {item.display_value} ({item.source})")
        lines.append("")
        lines.append("Recommended follow-up:")
        lines.extend(f"- {item}" for item in insight.recommended_follow_up)
    lines.extend(["", "## Known Facts", ""])
    for evidence_id in output.known_facts:
        item = evidence_map[evidence_id]
        lines.append(f"- `{evidence_id}`: {item.metric} = {item.display_value}")
    lines.extend(["", "## Unresolved Questions", ""])
    lines.extend(f"- {item}" for item in output.unresolved_questions)
    lines.extend(["", "## Recommended Actions", ""])
    lines.extend(f"- {item}" for item in output.recommended_actions)
    lines.extend(["", "## Confidence / Evidence Notes", ""])
    lines.extend(f"- {item}" for item in output.confidence_notes)
    return "\n".join(lines) + "\n"
