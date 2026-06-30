"""OpenAI Responses API reasoning provider for Brain 0.12.

Uses requests and strict JSON Schema structured output. The API result is still
revalidated locally. Nothing here executes actions or imports hardware.
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from ..action_validator import VALID_ACTION_TYPES, VALID_RISK_LEVELS, validate_all_candidates
from ..proposal import check_no_forbidden_reasoning_language
from ..provider_base import LLMProviderBase, ProviderConfig, ReasoningOutput

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIProvider(LLMProviderBase):
    def __init__(self, api_key: str | None = None, model: str | None = None, config: ProviderConfig | None = None):
        model = model or os.getenv("BEAN_LLM_MODEL", "gpt-4o-mini")
        super().__init__(config or ProviderConfig(name="openai", model=model))
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def ping(self) -> dict[str, Any]:
        return {"ok": bool(self.api_key), "provider": "openai", "model": self.config.model}

    def reason(self, context: dict[str, Any], instruction: str = "") -> ReasoningOutput:
        if not self.api_key:
            return ReasoningOutput("", "OpenAIProvider unavailable: missing OPENAI_API_KEY", provider="openai", error="missing_api_key")
        try:
            payload = self._build_request(context, instruction)
            response = requests.post(
                OPENAI_RESPONSES_URL,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            if response.status_code >= 400:
                return ReasoningOutput("", "OpenAI API error", provider="openai", error=f"http_{response.status_code}: {response.text[:500]}")
            text = self._extract_text(response.json())
            return self._parse_output(text)
        except Exception as exc:
            return ReasoningOutput("", "OpenAIProvider exception", provider="openai", error=str(exc))

    def _build_request(self, context: dict[str, Any], instruction: str) -> dict[str, Any]:
        return {
            "model": self.config.model,
            "input": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": json.dumps({"instruction": instruction, "context": context}, default=str)},
            ],
            "max_output_tokens": self.config.max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "bean_reasoning_output",
                    "strict": True,
                    "schema": self._json_schema(),
                }
            },
        }

    def _system_prompt(self) -> str:
        return (
            "You are a reasoning provider for BEAN. Return JSON only. "
            "You are not BEAN's identity. Do not claim sentience, emotion, or action. "
            "Produce proposed candidate records only. Do not execute anything. "
            "Motion remains disabled and must be supervisor-gated."
        )

    def _json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["reasoning_text", "summary", "confidence", "action_candidates", "referenced_hypothesis_ids"],
            "properties": {
                "reasoning_text": {"type": "string"},
                "summary": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "referenced_hypothesis_ids": {"type": "array", "items": {"type": "string"}},
                "action_candidates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["action_type", "rationale", "payload", "risk_level"],
                        "properties": {
                            "action_type": {"type": "string", "enum": sorted(VALID_ACTION_TYPES)},
                            "rationale": {"type": "string"},
                            "payload": {"type": "object"},
                            "risk_level": {"type": "string", "enum": sorted(VALID_RISK_LEVELS)},
                        },
                    },
                },
            },
        }

    def _extract_text(self, payload: dict[str, Any]) -> str:
        if payload.get("status") == "incomplete":
            raise ValueError("OpenAI response incomplete")
        output = payload.get("output") or []
        for item in output:
            for block in item.get("content", []) or []:
                if block.get("type") == "refusal":
                    raise ValueError("OpenAI response refusal")
                if "text" in block:
                    return block["text"]
        if "output_text" in payload:
            return payload["output_text"]
        raise ValueError("No text output in OpenAI response")

    def _parse_output(self, text: str) -> ReasoningOutput:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:].strip()
            data = json.loads(cleaned)
        except Exception as exc:
            return ReasoningOutput(text, "Could not parse provider JSON", provider="openai", error=f"json_parse_error: {exc}")
        ok, hits = check_no_forbidden_reasoning_language(str(data.get("reasoning_text", "")) + " " + str(data.get("summary", "")))
        if not ok:
            return ReasoningOutput("[redacted forbidden reasoning language]", "Rejected forbidden language", confidence=0.0, provider="openai", error=f"forbidden_language: {hits}")
        valid, rejected = validate_all_candidates(data.get("action_candidates") or [])
        return ReasoningOutput(
            reasoning_text=str(data.get("reasoning_text", "")),
            summary=str(data.get("summary", "")),
            confidence=max(0.0, min(1.0, float(data.get("confidence", 0.0)))),
            action_candidates=valid,
            referenced_hypothesis_ids=[str(x) for x in data.get("referenced_hypothesis_ids", [])],
            provider="openai",
            error=f"rejected_candidates: {rejected}" if rejected else None,
        )
