"""Authenticated BEAN MCP ASGI app for remote clients such as Perplexity.

Only the four existing public-safe, stateless tools are exported. This does
NOT expose the installed ChatGPT BEAN cloud memory plugin or local Core state.

Start with: uvicorn integrations.chatgpt.perplexity_remote:app --host 0.0.0.0 --port 10000
Requires BEAN_MCP_API_KEY (32+ printable non-space characters).
"""
from __future__ import annotations

import os
import re

from mcp.server.transport_security import TransportSecuritySettings

from integrations.chatgpt.perplexity_auth import BearerGate
from integrations.chatgpt.server import mcp

# Render sets this automatically for web services. Explicitly list only the
# actual expected hostname instead of disabling MCP's DNS-rebinding protection.
external_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip().lower()
if external_host and not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,251}[a-z0-9]", external_host):
    raise ValueError("Invalid RENDER_EXTERNAL_HOSTNAME")

allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
allowed_origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
if external_host:
    allowed_hosts.extend([external_host, external_host + ":*"])
    allowed_origins.extend(["https://" + external_host, "https://" + external_host + ":*"])

security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=allowed_hosts,
    allowed_origins=allowed_origins,
)

# Absence of a token must prevent public service startup, never permit anonymous use.
app = BearerGate(
    mcp.streamable_http_app(
        transport_security=security,
        stateless_http=True,
        json_response=True,
        max_request_body_size=32768,
    ),
    os.environ.get("BEAN_MCP_API_KEY", ""),
)
