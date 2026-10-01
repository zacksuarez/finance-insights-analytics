"""Orchestrate trusted-data gates, provider generation, and guardrails."""

from __future__ import annotations

from finance_ai.guardrails import GuardrailViolation, validate_ai_output
from finance_ai.models import EvidencePackage, ExecutiveInsightOutput, ValidationDiagnostic
from finance_ai.providers.base import AIInsightProvider


TRUST_FAILURE_MESSAGE = "Executive AI insights are unavailable because trusted finance data validation failed."


class InsightGenerationError(RuntimeError):
    def __init__(self, diagnostic: ValidationDiagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


class ExecutiveInsightService:
    def __init__(self, provider: AIInsightProvider) -> None:
        self.provider = provider

    def generate(self, context: EvidencePackage) -> ExecutiveInsightOutput:
        if not context.data_quality_status.passed or not context.reconciliation_status.passed:
            raise InsightGenerationError(ValidationDiagnostic(
                category="trusted_data_validation_failed",
                message=TRUST_FAILURE_MESSAGE,
                violations=(
                    context.data_quality_status.failed_controls
                    + context.reconciliation_status.failures
                ),
            ))
        if not context.priority_issues:
            output = ExecutiveInsightOutput(
                executive_summary="No deterministic priority issues were selected for executive interpretation.",
                top_insights=[],
                known_facts=[],
                unresolved_questions=[],
                recommended_actions=["Continue the established finance review cadence."],
                confidence_notes=["Trusted analytical controls passed and no priority issue met the selection rules."],
            )
            validate_ai_output(context, output)
            return output
        try:
            output = self.provider.generate(context)
        except InsightGenerationError:
            raise
        except Exception as exc:
            raise InsightGenerationError(ValidationDiagnostic(
                category="provider_generation_failed",
                message="Executive AI insights could not be generated safely.",
                violations=[type(exc).__name__],
            )) from exc
        try:
            validate_ai_output(context, output)
        except GuardrailViolation as exc:
            raise InsightGenerationError(ValidationDiagnostic(
                category="business_guardrail_failed",
                message="The generated response failed executive insight validation and was rejected.",
                violations=exc.violations,
            )) from exc
        return output
