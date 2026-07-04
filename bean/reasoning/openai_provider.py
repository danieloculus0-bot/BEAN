"""OpenAI provider for Brain 0.11.

Uses Python stdlib only. Tests remain offline-safe when OPENAI_API_KEY is absent.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

from .llm_adapter import LLMAdapterBase


class OpenAIProvider(LLMAdapterBase):
    adapter_name = "openai"

    def __init__(self, model_name: str | None = None, api_key: str | None = None, timeout_seconds: int = 45):
        self.model_name = model_name or os.environ.get("BEAN_OPENAI_MODEL", "gpt-5.5")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.timeout_seconds = int(timeout_seconds)
        base_url = os.environ.get("BEAN_OPENAI_BASE_URL", "https://api.openai.com")
        self.endpoint = base_url.rstrip("/") + "/v1/responses"

    def complete(self, prompt: str, context: dict | None = None) -> dict:
        if not self.api_key:
            return self._error("OPENAI_API_KEY not set")
        payload = {"model": self.model_name, "input": prompt, "temperature": 0.2, "tool_choice": "none"}
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text = self._extract_text(data)
            if not text:
                return self._error("provider response contained no output text")
            return {"ok": True, "raw_text": text, "adapter_name": self.adapter_name, "model_name": self.model_name, "provider_response_id": data.get("id")}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return self._error(f"provider HTTP {exc.code}: {body[:500]}")
        except Exception as exc:
            return self._error(str(exc))

    def _extract_text(self, data: dict) -> str:
        if isinstance(data.get("output_text"), str):
            return data["output_text"]
        parts = []
        for item in data.get("output", []) or []:
            for content in item.get("content", []) or []:
                if isinstance(content.get("text"), str):
                    parts.append(content["text"])
        return "\n".join(parts).strip()

    def _error(self, message: str) -> dict:
        return {"ok": False, "adapter_name": self.adapter_name, "model_name": self.model_name, "error": message}
