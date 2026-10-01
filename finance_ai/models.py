"""Strict V3 evidence and executive-insight contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Priority = Literal["high", "medium", "low"]
InsightCategory = Literal[
    "margin",
    "customer",
    "forecast",
    "pipeline",
    "opex",
    "concentration",
    "cross-functional",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EvidenceItem(ContractModel):
    evidence_id: str = Field(pattern=r"^[A-Z][A-Z0-9_]+$")
    metric: str
    value: float
    display_value: str
    unit: Literal["currency", "ratio", "percentage", "basis_points", "count"]
    source: str
    period: str
    entity_id: str
    entity_name: str


class EntityReference(ContractModel):
    entity_id: str
    entity_type: str
    entity_name: str


class PriorityIssue(ContractModel):
    issue_id: str
    period: str
    issue_type: str
    entity_id: str
    entity_type: str
    entity_name: str
    metric: str
    actual_value: float
    threshold: float
    severity: Literal["High", "Medium", "Low"]
    minimum_priority: Priority
    status: str
    priority_score: float
    priority_reasons: list[str]
    evidence_ids: list[str]


class ScenarioSummary(ContractModel):
    scenario_name: Literal["Base", "Upside", "Downside"]
    revenue_evidence_id: str
    margin_evidence_id: str
    contribution_evidence_id: str


class ReconciliationStatus(ContractModel):
    passed: bool
    tolerance: float
    checked_measures: int
    failures: list[str]


class DataQualityStatus(ContractModel):
    passed: bool
    v1_controls: int
    v2_controls: int
    failed_controls: list[str]
    required_marts_present: bool


class EvidencePackage(ContractModel):
    package_version: Literal["3.0"] = "3.0"
    period: str
    generated_from: Literal["verified_v2_analytics"] = "verified_v2_analytics"
    executive_kpis: list[str]
    priority_issues: list[PriorityIssue]
    customer_insights: list[str]
    margin_insights: list[str]
    forecast_insights: list[str]
    pipeline_insights: list[str]
    opex_insights: list[str]
    regional_insights: list[str]
    scenario_summary: list[ScenarioSummary]
    evidence: list[EvidenceItem]
    entity_catalog: list[EntityReference]
    reconciliation_status: ReconciliationStatus
    data_quality_status: DataQualityStatus


class ExecutiveInsight(ContractModel):
    insight_id: str = Field(pattern=r"^AI-[A-Z0-9-]+$")
    title: str = Field(min_length=5, max_length=120)
    priority: Priority
    category: InsightCategory
    summary: str = Field(min_length=15, max_length=500)
    issue_ids: list[str] = Field(min_length=1, max_length=6)
    evidence_ids: list[str] = Field(min_length=1, max_length=10)
    entity_ids: list[str] = Field(default_factory=list, max_length=10)
    business_implication: str = Field(min_length=10, max_length=400)
    recommended_follow_up: list[str] = Field(min_length=1, max_length=4)

    @field_validator("issue_ids", "evidence_ids", "entity_ids")
    @classmethod
    def reject_duplicate_references(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("reference lists must not contain duplicates")
        return values


class ExecutiveInsightOutput(ContractModel):
    executive_summary: str = Field(min_length=20, max_length=700)
    top_insights: list[ExecutiveInsight] = Field(max_length=8)
    known_facts: list[str] = Field(max_length=15)
    unresolved_questions: list[str] = Field(max_length=10)
    recommended_actions: list[str] = Field(max_length=10)
    confidence_notes: list[str] = Field(min_length=1, max_length=8)

    @field_validator("known_facts")
    @classmethod
    def known_facts_are_evidence_references(cls, values: list[str]) -> list[str]:
        for value in values:
            if not value or value != value.upper() or " " in value:
                raise ValueError("known_facts must contain evidence IDs only")
        return values


class ValidationDiagnostic(ContractModel):
    category: str
    message: str
    violations: list[str] = Field(default_factory=list)
