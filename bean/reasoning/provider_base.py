"""Provider interface for BEAN reasoning.

Providers return structured text and candidate records. They do not mutate
memory directly and they do not execute actions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderConfig:
    name: str = "stub"
    model: str = "stub"
    timeout_seconds: int = 30
    max_output_tokens: int = 1200


@dataclass
class ReasoningOutput:
    reasoning_text: str
    summary: str
    confidence: float = 0.0
    action_candidates: list[dict[str, Any]] = field(default_factory=list)
    referenced_hypothesis_ids: list[str] = field(default_factory=list)
    provider: str = "unknown"
    tokens_used: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "reasoning_text": self.reasoning_text,
            "summary": self.summary,
            "confidence": self.confidence,
            "action_candidates": list(self.action_candidates),
            "referenced_hypothesis_ids": list(self.referenced_hypothesis_ids),
            "provider": self.provider,
            "tokens_used": self.tokens_used,
            "error": self.error,
        }


class LLMProviderBase(ABC):
    def __init__(self, config: ProviderConfig | None = None):
        self.config = config or ProviderConfig()

    @abstractmethod
    def ping(self) -> dict[str, Any]:
        """Return provider health without producing a reasoning proposal."""

    @abstractmethod
    def reason(self, context: dict[str, Any], instruction: str = "") -> ReasoningOutput:
        """Return a structured reasoning output. Never execute actions."""
