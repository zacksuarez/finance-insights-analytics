"""Transparent deterministic issue prioritization."""

from __future__ import annotations

import re
from typing import Any


SEVERITY_SCORES = {"High": 60.0, "Medium": 35.0, "Low": 15.0}
TYPE_SCORES = {
    "Pipeline Coverage Weakness": 14.0,
    "Forecast Accuracy Deterioration": 13.0,
    "Margin Deterioration": 12.0,
    "Customer Profitability Deterioration": 10.0,
    "Structural OpEx Overrun": 9.0,
    "Customer Concentration Risk": 7.0,
}
MINIMUM_PRIORITY = {"High": "high", "Medium": "medium", "Low": "low"}


def entity_id(entity_type: str, entity_name: str, issue_id: str = "") -> str:
    if entity_type == "Customer" and "CUST" in issue_id:
        customer_id = issue_id.rsplit("-", 1)[-1]
        return f"CUSTOMER_{customer_id}"
    normalized = re.sub(r"[^A-Z0-9]+", "_", entity_name.upper()).strip("_")
    prefix = re.sub(r"[^A-Z0-9]+", "_", entity_type.upper()).strip("_")
    return f"{prefix}_{normalized}"


def issue_evidence_id(issue_id: str) -> str:
    return "ISSUE_" + re.sub(r"[^A-Z0-9]+", "_", issue_id.upper()).strip("_")


def _breach_score(actual: float, threshold: float) -> float:
    denominator = max(abs(threshold), 1e-9)
    return min(abs(actual - threshold) / denominator * 20.0, 20.0)


def score_issue(issue: dict[str, Any]) -> tuple[float, list[str]]:
    severity = issue["severity"]
    issue_type = issue["issue_type"]
    score = SEVERITY_SCORES[severity] + TYPE_SCORES.get(issue_type, 5.0)
    reasons = [f"{severity.lower()} deterministic severity"]

    breach = _breach_score(float(issue["actual_value"]), float(issue["threshold"]))
    score += breach
    reasons.append("material threshold breach")

    if issue_type in {"Pipeline Coverage Weakness", "Forecast Accuracy Deterioration"}:
        score += 8.0
        reasons.append("forward-looking relevance")
    if issue["entity_type"] == "Company":
        score += 6.0
        reasons.append("company-wide impact")
    if issue_type == "Structural OpEx Overrun":
        match = re.search(r"(\d+) material months", issue.get("supporting_metric", ""))
        if match:
            score += min(float(match.group(1)), 6.0) * 2.0
            reasons.append("persistent trailing-period breach")
    if issue_type == "Customer Profitability Deterioration":
        match = re.search(r"Revenue rank (\d+)", issue.get("supporting_metric", ""))
        if match:
            score += max(0.0, 11.0 - float(match.group(1)))
            reasons.append("revenue concentration relevance")
    return round(score, 3), reasons


def prioritize_issues(issues: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    """Rank issues while retaining at least one issue from every triggered rule type."""
    scored: list[dict[str, Any]] = []
    for issue in issues:
        score, reasons = score_issue(issue)
        enriched = dict(issue)
        enriched["priority_score"] = score
        enriched["priority_reasons"] = reasons
        enriched["minimum_priority"] = MINIMUM_PRIORITY[issue["severity"]]
        enriched["entity_id"] = entity_id(issue["entity_type"], issue["entity_name"], issue["issue_id"])
        enriched["evidence_ids"] = [issue_evidence_id(issue["issue_id"])]
        scored.append(enriched)

    ordered = sorted(scored, key=lambda item: (-item["priority_score"], item["issue_id"]))
    selected: list[dict[str, Any]] = []
    covered_types: set[str] = set()
    for issue in ordered:
        if issue["issue_type"] not in covered_types:
            selected.append(issue)
            covered_types.add(issue["issue_type"])
    for issue in ordered:
        if issue not in selected and len(selected) < limit:
            selected.append(issue)
    return sorted(selected[:limit], key=lambda item: (-item["priority_score"], item["issue_id"]))
