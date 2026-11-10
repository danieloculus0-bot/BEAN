"""Small fail-closed ASGI bearer gate for BEAN's remote MCP preview.

This authenticates the transport, not any shared memory or production data.
The existing local-only MCP server remains unchanged.
"""
from __future__ import annotations

import hmac
from typing import Any, Callable


class BearerGate:
    """Require a single Authorization: Bearer <key> on every MCP request."""

    def __init__(self, inner: Callable[..., Any], token: str):
        if not isinstance(token, str) or len(token) < 32:
            raise ValueError("BEAN_MCP_API_KEY must contain at least 32 characters")
        if any(ord(ch) < 33 or ord(ch) > 126 for ch in token):
            raise ValueError("BEAN_MCP_API_KEY must be printable without whitespace")
        self.inner = inner
        self.expected = ("Bearer " + token).encode("ascii")

    @staticmethod
    async def reply(send: Callable[..., Any], code: int, body: bytes = b"") -> None:
        headers = [(b"content-type", b"text/plain; charset=utf-8"),
                   (b"content-length", str(len(body)).encode("ascii"))]
        if code == 401:
            headers.append((b"www-authenticate", b"Bearer"))
        await send({"type": "http.response.start", "status": code, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope: dict, receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope["type"] == "lifespan":
            await self.inner(scope, receive, send)
            return
        if scope["type"] != "http":
            return
        path = scope.get("path", "")
        if path == "/health" and scope.get("method") == "GET":
            await self.reply(send, 200, b"ok")
            return
        if path != "/mcp":
            await self.reply(send, 404, b"not found")
            return
        authorization = [v for k, v in scope.get("headers", [])
                         if k.lower() == b"authorization"]
        if len(authorization) != 1 or not hmac.compare_digest(authorization[0], self.expected):
            await self.reply(send, 401, b"unauthorized")
            return
        await self.inner(scope, receive, send)
