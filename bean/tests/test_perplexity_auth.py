"""Dependency-free ASGI transport authentication checks for remote MCP."""
from __future__ import annotations

import asyncio

import pytest

from integrations.chatgpt.perplexity_auth import BearerGate

TOKEN = "sample-auth-token-" + "x" * 48


def _request(gate, path="/mcp", method="POST", headers=()):
    events = []
    forwarded = []

    async def inner_receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event):
        events.append(event)

    scope = {"type": "http", "path": path, "method": method, "headers": list(headers)}
    asyncio.run(gate(scope, inner_receive, send))
    return events


async def _fake_inner(scope, receive, send):
    await send({"type": "http.response.start", "status": 204, "headers": []})
    await send({"type": "http.response.body", "body": b""})


def test_gate_fails_closed_without_valid_key():
    for token in ("", "short", "a" * 31, "a" * 32 + "\n"):
        with pytest.raises(ValueError):
            BearerGate(_fake_inner, token)


def test_mcp_auth_required_and_duplicate_headers_rejected():
    gate = BearerGate(_fake_inner, TOKEN)
    assert _request(gate)[0]["status"] == 401
    assert _request(gate, headers=[(b"authorization", b"Bearer wrong")])[0]["status"] == 401
    assert _request(gate, headers=[
        (b"authorization", ("Bearer " + TOKEN).encode()),
        (b"authorization", ("Bearer " + TOKEN).encode()),
    ])[0]["status"] == 401
    allowed = _request(gate, headers=[(b"authorization", ("Bearer " + TOKEN).encode())])
    assert allowed[0]["status"] == 204


def test_health_is_public_but_no_other_route_exposed():
    gate = BearerGate(_fake_inner, TOKEN)
    assert _request(gate, path="/health", method="GET")[0]["status"] == 200
    assert _request(gate, path="/")[0]["status"] == 404
    assert _request(gate, path="/health", method="POST")[0]["status"] == 404
