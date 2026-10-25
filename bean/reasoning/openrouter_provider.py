"""Optional real OpenRouter provider; all learning policy remains BEAN-owned.

Uses a pinned no-token-charge Nemotron model by default, with no paid fallback.
The adapter returns actual model text + served identity (not synthetic output).
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .llm_adapter import LLMAdapterBase


class OpenRouterProvider(LLMAdapterBase):
    adapter_name = "openrouter"

    def __init__(self, model_name=None, api_key=None, requester=urlopen):
        self.model_name = model_name or os.environ.get(
            "BEAN_OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
        if not isinstance(self.model_name, str) or not self.model_name.endswith(":free"):
            raise ValueError("BEAN research provider requires an explicitly free model")
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self._requester = requester
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def complete(self, prompt, context=None):
        if not self.api_key:
            return {"ok": False, "error": "OPENROUTER_API_KEY not set",
                    "adapter_name": self.adapter_name, "model_name": self.model_name}
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 25000:
            raise ValueError("Bounded question/prompt required")
        # For native reasoning, the second parameter contains only BEAN's
        # selected source-backed lesson text, never the evaluator answer.
        if isinstance(context, str) and context:
            user = prompt + "\n\nPreviously measured BEAN lesson:\n" + context
        else:
            user = prompt
        if len(user) > 33000:
            raise ValueError("Reasoning context exceeds supported size")
        payload = {
            "model": self.model_name,
            "max_tokens": 1536,
            "messages": [
                {"role": "system", "content":
                 "Reason carefully using only supplied task evidence. "
                 "If uncertain, say so. Do not invent evidence or actions."},
                {"role": "user", "content": user},
            ],
        }
        req = Request(self.endpoint, data=json.dumps(payload).encode("utf-8"),
                      method="POST", headers={
                          "Authorization": "Bearer " + self.api_key,
                          "Content-Type": "application/json",
                          "X-Title": "BEAN Core Reasoning"})
        try:
            with self._requester(req, timeout=90) as r:
                data = json.loads(r.read(500000).decode("utf-8"))
        except HTTPError as exc:
            return {"ok": False, "error": "OpenRouter HTTP " + str(exc.code),
                    "adapter_name": self.adapter_name, "model_name": self.model_name}
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            return {"ok": False, "error": "OpenRouter transport " + type(exc).__name__,
                    "adapter_name": self.adapter_name, "model_name": self.model_name}
        choices = data.get("choices") or []
        answer = (choices[0].get("message", {}).get("content")
                  if choices and isinstance(choices[0], dict) else None)
        served = data.get("model")
        if not isinstance(served, str) or served != self.model_name:
            return {"ok": False, "error": "Served model identity mismatch",
                    "adapter_name": self.adapter_name, "model_name": self.model_name}
        if not isinstance(answer, str) or not answer.strip():
            return {"ok": False, "error": "Empty provider response",
                    "adapter_name": self.adapter_name, "model_name": self.model_name}
        return {"ok": True, "raw_text": answer.strip(),
                "adapter_name": self.adapter_name, "model_name": served,
                "provider_response_id": data.get("id"),
                "verified_outcome": False}
