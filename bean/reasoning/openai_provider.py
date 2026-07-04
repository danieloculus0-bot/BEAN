"""OpenAI provider placeholder for Brain 0.11.

OpenAI is the preferred real reasoning provider. This module is intentionally
safe to import offline; tests use MockLLMAdapter.
"""

import os
from .llm_adapter import LLMAdapterBase


class OpenAIProvider(LLMAdapterBase):
    adapter_name = "openai"

    def __init__(self, model_name: str = "gpt-4.1-mini", api_key: str | None = None):
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def complete(self, prompt: str, context: dict | None = None) -> dict:
        if not self.api_key:
            return {"ok": False, "adapter_name": self.adapter_name, "model_name": self.model_name, "error": "OPENAI_API_KEY not set"}
        return {"ok": False, "adapter_name": self.adapter_name, "model_name": self.model_name, "error": "network call intentionally deferred in repo tests"}
