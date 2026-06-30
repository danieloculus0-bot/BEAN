"""Reasoning providers."""

from .stub_provider import StubProvider

try:
    from .openai_provider import OpenAIProvider
except Exception:  # requests may be absent in tiny offline test envs
    OpenAIProvider = None

__all__ = ["StubProvider", "OpenAIProvider"]
