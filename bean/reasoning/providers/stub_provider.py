"""Deterministic offline reasoning provider."""

from __future__ import annotations

from typing import Any

from ..provider_base import LLMProviderBase, ProviderConfig, ReasoningOutput


class StubProvider(LLMProviderBase):
    def __init__(self, config: ProviderConfig | None = None):
        super().__init__(config or ProviderConfig(name="stub", model="deterministic-stub"))

    def ping(self) -> dict[str, Any]:
        return {"ok": True, "provider": "stub", "model": self.config.model}

    def reason(self, context: dict[str, Any], instruction: str = "") -> ReasoningOutput:
        speculative = context.get("speculative_summary", {}) or {}
        candidates: list[dict[str, Any]] = []
        if speculative.get("unresolved_count", 0):
            candidates.append({
                "action_type": "ask_clarification",
                "rationale": "There are unresolved hypotheses that need supervisor clarification.",
                "payload": {"unresolved_count": speculative.get("unresolved_count", 0)},
                "risk_level": "low",
            })
        else:
            candidates.append({
                "action_type": "propose_observation",
                "rationale": "No unresolved hypothesis dominates the current context; observe before acting.",
                "payload": {"motion_enabled": False},
                "risk_level": "low",
            })
        return ReasoningOutput(
            reasoning_text="Stub reasoning completed from current context without claiming sentience or executing actions.",
            summary="Offline stub produced safe proposed candidate records only.",
            confidence=0.35,
            action_candidates=candidates,
            referenced_hypothesis_ids=[h.get("hypothesis_id") for h in speculative.get("open_hypotheses", []) if h.get("hypothesis_id")],
            provider="stub",
            tokens_used=0,
        )
