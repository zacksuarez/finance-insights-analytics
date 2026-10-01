"""Central AI provider configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AIConfig:
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    timeout_seconds: float = 45.0
    max_retries: int = 1
    temperature: float | None = 0.1
    reasoning_effort: str | None = None

    @classmethod
    def from_environment(cls) -> "AIConfig":
        temperature = os.getenv("AI_TEMPERATURE", "0.1").strip()
        reasoning = os.getenv("AI_REASONING_EFFORT", "").strip()
        return cls(
            provider=os.getenv("AI_PROVIDER", "openai").strip().lower(),
            model=os.getenv("AI_MODEL", "gpt-4.1-mini").strip(),
            timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "45")),
            max_retries=int(os.getenv("AI_MAX_RETRIES", "1")),
            temperature=float(temperature) if temperature else None,
            reasoning_effort=reasoning or None,
        )
