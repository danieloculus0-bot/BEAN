"""Replaceable OpenRouter adapter; BEAN owns all reasoning memory/policy.

Default is a free model. An inexpensive paid model is separately allowlisted,
disabled by default, bounded per instance, and NEVER an automatic fallback.
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
        self.low_cost_paid = self.model_name == "qwen/qwen3.5-flash-02-23"
        if self.low_cost_paid:
            if os.environ.get("BEAN_OPENROUTER_PAID_ENABLED") != "1":
                raise ValueError("Paid provider disabled; explicit opt-in required")
            limit = os.environ.get("BEAN_OPENROUTER_PAID_CALL_LIMIT", "0")
            if not limit.isdecimal() or not 1 <= int(limit) <= 100:
                raise ValueError("Paid model needs 1..100 explicit per-instance calls")
            self.paid_call_limit = int(limit)
        elif not isinstance(self.model_name, str) or not self.model_name.endswith(":free"):
            raise ValueError("Provider must be explicitly free or the pinned cheap model")
        self.paid_calls_attempted = 0
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self._requester = requester
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.last_failure_kind = None

    def free_request_budget(self):
        """Read free-model daily quota without spending an inference request.

        Only numeric usage is exposed. Never return API key labels, balances,
        account identifiers, raw provider error bodies, or headers.
        """
        if not self.api_key:
            return {"status": "missing_key"}
        req = Request("https://openrouter.ai/api/v1/key",
                      method="GET", headers={
                          "Authorization": "Bearer " + self.api_key,
                          "Accept": "application/json"})
        try:
            with self._requester(req, timeout=8) as result:
                payload = json.loads(result.read(16001).decode("utf-8"))
            usage = (payload.get("data") or {}).get("free_model_daily_requests")
            if not isinstance(usage, dict):
                return {"status": "quota_not_reported"}
            fields = {key: usage.get(key) for key in ("used", "limit", "remaining")}
            if not all(type(value) is int and value >= 0
                       for value in fields.values()):
                return {"status": "quota_not_reported"}
            return {"status": "available", **fields}
        except HTTPError as exc:
            return {"status": "quota_check_failed", "http_status": int(exc.code)}
        except (URLError, TimeoutError, OSError, ValueError, RuntimeError,
                TypeError, AttributeError) as exc:
            return {"status": "quota_check_failed",
                    "error_class": type(exc).__name__}

    def complete(self, prompt, context=None):
        self.last_failure_kind = None
        if not self.api_key:
            self.last_failure_kind = "credentials_missing"
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
        if self.low_cost_paid:
            # This is a per-Python-instance ceiling, not a cross-process
            # account-wide spending guarantee. Set a cap on the provider key.
            if self.paid_calls_attempted >= self.paid_call_limit:
                self.last_failure_kind = "paid_call_budget_exhausted"
                return {"ok": False, "error": "Explicit paid request cap reached",
                        "adapter_name": self.adapter_name, "model_name": self.model_name}
            if len(user) > 10000:
                raise ValueError("Paid prompt exceeds bounded 10K-char budget")
            self.paid_calls_attempted += 1
        payload = {
            "model": self.model_name,
            "max_tokens": 512 if self.low_cost_paid else 1536,
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
            self.last_failure_kind = "http_" + str(exc.code)
            return {"ok": False, "error": "OpenRouter HTTP " + str(exc.code),
                    "adapter_name": self.adapter_name, "model_name": self.model_name}
        except (URLError, TimeoutError, OSError, ValueError, RuntimeError) as exc:
            self.last_failure_kind = "transport_" + type(exc).__name__
            return {"ok": False, "error": "OpenRouter transport " + type(exc).__name__,
                    "adapter_name": self.adapter_name, "model_name": self.model_name}
        if not isinstance(data, dict):
            self.last_failure_kind = "invalid_response_structure"
            return {"ok": False, "error": "OpenRouter returned malformed response",
                    "adapter_name": self.adapter_name, "model_name": self.model_name}
        choices = data.get("choices") or []
        answer = (choices[0].get("message", {}).get("content")
                  if choices and isinstance(choices[0], dict) else None)
        served = data.get("model")
        if not isinstance(served, str) or served != self.model_name:
            self.last_failure_kind = "served_model_identity_mismatch"
            return {"ok": False, "error": "Served model identity mismatch",
                    "adapter_name": self.adapter_name, "model_name": self.model_name}
        if not isinstance(answer, str) or not answer.strip():
            self.last_failure_kind = "empty_provider_answer"
            return {"ok": False, "error": "Empty provider response",
                    "adapter_name": self.adapter_name, "model_name": self.model_name}
        usage = data.get("usage") or {}
        if not isinstance(usage, dict):
            usage = {}
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        # OpenRouter published Qwen Flash rates as of October 2026.
        # These are estimates, not billing reconciliation or a price lock.
        estimated_usd = None
        if (self.low_cost_paid and type(prompt_tokens) is int
                and type(completion_tokens) is int
                and prompt_tokens >= 0 and completion_tokens >= 0):
            estimated_usd = round(
                (prompt_tokens * 0.065 + completion_tokens * 0.26) / 1000000, 9)
        return {"ok": True, "raw_text": answer.strip(),
                "adapter_name": self.adapter_name, "model_name": served,
                "provider_response_id": data.get("id"),
                "estimated_provider_cost_usd": estimated_usd,
                "verified_outcome": False}
