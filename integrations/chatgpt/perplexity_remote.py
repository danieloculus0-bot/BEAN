"""Authenticated BEAN MCP ASGI app for remote clients such as Perplexity.

Only the four existing public-safe, stateless tools are exported. This does
NOT expose the installed ChatGPT BEAN cloud memory plugin or local Core state.

Start with: uvicorn integrations.chatgpt.perplexity_remote:app --host 0.0.0.0 --port 10000
Requires BEAN_MCP_API_KEY (32+ printable non-space characters).
"""
from __future__ import annotations

import os

from integrations.chatgpt.perplexity_auth import BearerGate
from integrations.chatgpt.server import mcp

# Absence of a token must prevent public service startup, never permit anonymous use.
app = BearerGate(
    mcp.streamable_http_app(
        host="0.0.0.0",
        stateless_http=True,
        json_response=True,
        max_request_body_size=32768,
    ),
    os.environ.get("BEAN_MCP_API_KEY", ""),
)
