"""Local-only Ollama conversation transport for BEAN's optional voice interface.

No API key or third-party Python dependency. Ollama's installed text model
generates replies; this adapter has no code-execution or body-control tools.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener


class OllamaError(RuntimeError):
    """A clear, user-facing Ollama connection or reply failure."""


def validated_local_url(value: str) -> str:
    """Never silently send BEAN conversations to a remote model host."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        raise ValueError("Invalid Ollama URL") from None
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or port is None
    ):
        raise ValueError("BEAN voice mode accepts only a local Ollama HTTP address, such as http://127.0.0.1:11434")
    return value.rstrip("/")


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434",
                 timeout: int = 180, opener=None):
        self.base_url = validated_local_url(base_url)
        self.timeout = timeout
        # Do not use workstation HTTP proxy settings for local conversations.
        self._open = opener or build_opener(ProxyHandler({})).open

    def _json(self, route: str, body: dict | None = None) -> dict:
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = Request(
            self.base_url + route,
            data=payload,
            method="GET" if payload is None else "POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with self._open(req, timeout=self.timeout) as response:
                data = response.read(2_000_001)
        except HTTPError as exc:
            raise OllamaError(f"Ollama HTTP {exc.code}; check that your model is available") from None
        except (URLError, OSError, TimeoutError) as exc:
            raise OllamaError(
                "Cannot reach local Ollama. Make sure it is running on 127.0.0.1:11434."
            ) from exc
        if len(data) > 2_000_000:
            raise OllamaError("Ollama response exceeded the local size limit")
        try:
            result = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OllamaError("Ollama returned invalid JSON") from exc
        if not isinstance(result, dict):
            raise OllamaError("Ollama returned an invalid response object")
        if result.get("error"):
            raise OllamaError("Ollama reported: " + str(result["error"])[:250])
        return result

    def models(self) -> list[str]:
        result = self._json("/api/tags")
        entries = result.get("models", [])
        if not isinstance(entries, list):
            raise OllamaError("Ollama model list has an unexpected format")
        names = []
        for model in entries:
            if not isinstance(model, dict):
                continue
            name = model.get("name") or model.get("model")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        return names

    def select_model(self, requested: str | None = None) -> str:
        names = self.models()
        if requested:
            if requested not in names:
                raise OllamaError(
                    f"Model {requested!r} is not installed. Check 'ollama list' or install it first."
                )
            return requested
        chat_candidates = [
            name for name in names
            if "embed" not in name.lower() and "rerank" not in name.lower()
        ]
        if not chat_candidates:
            raise OllamaError(
                "No Ollama chat model is installed yet. Check 'ollama list' and pull a chat model."
            )
        return chat_candidates[0]

    def chat(self, model: str, messages: list[dict]) -> str:
        if not model or not messages:
            raise ValueError("Model and conversation are required")
        result = self._json("/api/chat", {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.55, "num_predict": 220, "num_ctx": 4096},
        })
        message = result.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise OllamaError("Ollama supplied no conversational reply")
        reply = message["content"].strip()
        if not reply:
            raise OllamaError("Ollama supplied an empty conversational reply")
        return reply[:6000]


    def chat_json(self, model: str, messages: list[dict], schema: dict | None = None) -> str:
        """Request constrained JSON output for BEAN's structured reasoning layer.

        Shares the loopback-only transport, proxy bypass and bounded response
        handling used by BEAN's conversational client. Never runs commands.
        """
        if not model or not messages:
            raise ValueError("Model and conversation are required")
        result = self._json("/api/chat", {
            "model": model,
            "messages": messages,
            "stream": False,
            "format": schema if schema is not None else "json",
            "options": {"temperature": 0.0, "num_predict": 512, "num_ctx": 4096, "repeat_penalty": 1.2},
        })
        message = result.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise OllamaError("Ollama supplied no structured reply")
        reply = message["content"].strip()
        if not reply:
            raise OllamaError("Ollama supplied an empty structured reply")
        # Do not silently truncate JSON: keep the full response for parse-failure receipts.
        if len(reply) > 20000:
            raise OllamaError("Ollama structured reply exceeded size limit")
        return reply
