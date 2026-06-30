"""Reasoning engine for Brain 0.11.

Runs provider reasoning, validates output, and persists proposed records only.
"""

from __future__ import annotations

from typing import Any

from .action_validator import validate_all_candidates
from .context_builder import build_reasoning_context
from .proposal import ReasoningProposal, get_pending_candidates, get_pending_proposals, persist_proposal
from .provider_base import LLMProviderBase


def run_reasoning_cycle(session_uuid: str, provider: LLMProviderBase, instruction: str = "", conn=None) -> dict[str, Any]:
    context = build_reasoning_context(session_uuid, conn=conn)
    output = provider.reason(context, instruction=instruction)
    valid_candidates, rejected_candidates = validate_all_candidates(output.action_candidates)
    proposal = ReasoningProposal(
        session_uuid=session_uuid,
        source_context=context,
        reasoning_text=output.reasoning_text,
        summary=output.summary,
        confidence=output.confidence,
        provider=output.provider,
        action_candidates=valid_candidates,
        referenced_hypothesis_ids=output.referenced_hypothesis_ids,
    )
    proposal_id = persist_proposal(conn, proposal)
    return {
        "ok": True,
        "proposal_id": proposal_id,
        "provider": output.provider,
        "rejected_candidates": rejected_candidates,
        "provider_error": output.error,
        "motion_enabled": False,
        "executed": False,
    }


__all__ = ["run_reasoning_cycle", "get_pending_proposals", "get_pending_candidates"]
