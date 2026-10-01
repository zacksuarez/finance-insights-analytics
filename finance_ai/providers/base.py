"""Provider-neutral executive insight interface."""

from __future__ import annotations

from typing import Protocol

from finance_ai.models import EvidencePackage, ExecutiveInsightOutput


class AIInsightProvider(Protocol):
    def generate(self, context: EvidencePackage) -> ExecutiveInsightOutput:
        """Generate structured interpretation without changing deterministic facts."""
