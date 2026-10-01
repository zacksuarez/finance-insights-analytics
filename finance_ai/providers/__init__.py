"""AI provider adapters."""

from finance_ai.providers.base import AIInsightProvider
from finance_ai.providers.openai_provider import OpenAIInsightProvider

__all__ = ["AIInsightProvider", "OpenAIInsightProvider"]
