"""Provider-neutral HTTP client. Agent integrations own their local profile."""
from __future__ import annotations

import json
from urllib.request import Request, build_opener, ProxyHandler

from .protocol import validate_message


class AgentClient:
    def __init__(self, base_url: str, token: str):
        if not isinstance(base_url, str) or not base_url.startswith("http://127.0.0.1:"):
            raise ValueError("prototype client requires explicit local relay")
        if not isinstance(token, str) or len(token) < 24:
            raise ValueError("agent capability missing")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._open = build_opener(ProxyHandler({})).open

    def _call(self, path: str, *, payload: dict | None = None):
        headers = {"Authorization": "Bearer " + self.token}
        body = None
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = Request(self.base_url + path, body, headers=headers,
                      method="POST" if body is not None else "GET")
        with self._open(req, timeout=5) as response:
            return json.loads(response.read(16384))

    def send(self, outbound: dict) -> dict:
        return self._call("/v1/messages", payload=validate_message(outbound))

    def inbox(self) -> list[dict]:
        return self._call("/v1/inbox")["messages"]
