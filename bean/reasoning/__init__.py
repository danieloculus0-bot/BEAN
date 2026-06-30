"""Brain 0.11 and 0.12 reasoning package."""

from __future__ import annotations

import os

from .provider_base import LLMProviderBase, ProviderConfig, ReasoningOutput
from .providers.stub_provider import StubProvider
from .reasoning_engine import run_reasoning_cycle
from .proposal import (
    ReasoningProposal,
    decide_action_candidate,
    get_pending_candidates,
    get_pending_proposals,
    get_proposal,
    init_reasoning_schema,
)


def get_provider(force_stub: bool = False) -> LLMProviderBase:
    if force_stub or not os.getenv("OPENAI_API_KEY"):
        return StubProvider()
    try:
        from .providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    except Exception:
        return StubProvider()


def init_reasoning(conn=None, force_stub: bool = False) -> LLMProviderBase:
    init_reasoning_schema(conn)
    return get_provider(force_stub=force_stub)


__all__ = [
    "LLMProviderBase",
    "ProviderConfig",
    "ReasoningOutput",
    "ReasoningProposal",
    "StubProvider",
    "get_provider",
    "init_reasoning",
    "init_reasoning_schema",
    "run_reasoning_cycle",
    "get_proposal",
    "get_pending_proposals",
    "get_pending_candidates",
    "decide_action_candidate",
]
