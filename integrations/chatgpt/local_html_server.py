"""Opt-in local BEAN HTML tools. This is NOT the public BEAN MCP service.

Use in a trusted desktop session only. The host must configure a limited
BEAN_HTML_ROOT; remote origins are denied unless explicitly listed.
The browser loads no user profile and cannot write files or execute shell.
"""
from __future__ import annotations

import os
from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from bean.integration.html_browser import inspect_html

mcp = MCPServer(
    "bean-html-browser-local",
    version="0.1.0",
    instructions=(
        "These local-only HTML inspection tools use an isolated Chromium "
        "context. Inspect first to view raw HTML and scripts without executing "
        "page JavaScript. Use run only when page execution is intended; page "
        "scripts are untrusted. Access is limited to BEAN_HTML_ROOT and "
        "explicit BEAN_HTML_ALLOWED_ORIGINS; no browser user profile is loaded. "
        "Do not treat a rendered page as an authenticated fact or upload "
        "private source, screenshots, or extracted data to public GitHub. "
        "Source inspection and JS execution are different operations."
    ),
)


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    title="BEAN: Inspect HTML source and embedded scripts",
    readOnlyHint=True, destructiveHint=False, idempotentHint=True,
    openWorldHint=False,
))
def bean_html_inspect(target: str) -> dict[str, Any]:
    """Inspect an authorized local .html page or explicitly permitted URL.

    Page JavaScript is disabled. Returns source and DOM excerpts, embedded
    inline scripts, external script links, sha256 hashes and blocked requests.
    The local filesystem root must be configured before calling the tool.
    """
    return inspect_html(target, execute_scripts=False)


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    title="BEAN: Run HTML JavaScript in an isolated local Chromium context",
    readOnlyHint=False, destructiveHint=False, idempotentHint=False,
    openWorldHint=False,
))
def bean_html_run(target: str, actions: list[dict[str, str]] | None = None,
                  wait_ms: int = 100) -> dict[str, Any]:
    """Run authorized HTML and interact with up to eight click/fill actions.

    This runs untrusted page JavaScript inside isolated browser sandbox, not
    Python, Node or BEAN Core. No browser credentials, direct filesystem
    writes, arbitrary remote networks, or persistent browser state.
    """
    return inspect_html(target, execute_scripts=True,
                        actions=actions, wait_ms=wait_ms)


def main() -> None:
    if not os.environ.get("BEAN_HTML_ROOT"):
        raise ValueError("Set BEAN_HTML_ROOT to a private, authorized local directory")
    raw = os.environ.get("BEAN_HTML_PORT", "8002")
    port = int(raw)
    if not 1 <= port <= 65535:
        raise ValueError("BEAN_HTML_PORT out of range")
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=port,
        stateless_http=True,
        json_response=True,
        max_request_body_size=16384,
    )


if __name__ == "__main__":
    main()
