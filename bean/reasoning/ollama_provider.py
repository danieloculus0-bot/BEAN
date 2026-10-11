"""Opt-in local Ollama reasoning provider for BEAN.

This is a proposal-only LLM adapter, not an action executor. The shared
Ollama transport rejects non-loopback URLs and bypasses HTTP proxies.
"""
from __future__ import annotations

import os

from ..voice.ollama import OllamaClient
from .llm_adapter import LLMAdapterBase
from .prompt_builder import OLLAMA_RESPONSE_SCHEMA


class OllamaProvider(LLMAdapterBase):
    adapter_name = "ollama"

    def __init__(self, model_name: str | None = None, client=None, timeout_seconds: int = 180):
        self.model_name = model_name or os.environ.get("BEAN_OLLAMA_MODEL", "qwen2.5-coder:1.5b")
        self.client = client if client is not None else OllamaClient(
            base_url=os.environ.get("BEAN_OLLAMA_URL", "http://127.0.0.1:11434"),
            timeout=timeout_seconds,
        )

    def complete(self, prompt: str, context: dict | None = None) -> dict:
        try:
            raw_text = self.client.chat_json(
                self.model_name,
                [{"role": "user", "content": prompt}],
                schema=OLLAMA_RESPONSE_SCHEMA,
            )
            if not raw_text:
                raise ValueError("Ollama returned an empty structured reply")
            return {
                "ok": True,
                "raw_text": raw_text,
                "adapter_name": self.adapter_name,
                "model_name": self.model_name,
            }
        except Exception as exc:
            # BEAN's existing reasoning engine records an unavailable-provider
            # proposal instead of accepting a missing model response as fact.
            return {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "adapter_name": self.adapter_name,
                "model_name": self.model_name,
            }
