"""Opt-in local BEAN <-> Axiom MCP navigation tools for ChatGPT.

Run on the same host as Axiom after installing the MCP SDK:
    python -m integrations.chatgpt.axiom_server

This is a separate local-only server, not the anonymous public evidence demo.
No model inference, no direct SQL writes, no unauthenticated internet service.
A hosted ChatGPT plugin cannot access the user's localhost without a secure,
authorized connection; the endpoint must not be published as-is.
"""
from __future__ import annotations

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from .axiom_navigation import AxiomNavigationClient

mcp = MCPServer(
    "bean-axiom-navigation-local",
    version="0.1.0",
    instructions=(
        "Use these tools when the user asks to find an Axiom screen, show their "
        "saved Favorites menu, pin a specific registered Axiom screen, or "
        "remove a favorite. Do not claim a favorite was added until a pin "
        "tool call returns saved=true. Do not invent routes; all returned "
        "paths are local to Axiom. Suggest a destination first if ambiguous. "
        "Tool calls are separate from BEAN Core thinking and language rendering."
    ),
)


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    title="BEAN: Find Axiom navigation links",
    readOnlyHint=True, destructiveHint=False, idempotentHint=True,
    openWorldHint=False,
))
def bean_find_axiom_pages(query: str) -> dict:
    """Find real Axiom screens to offer as navigation links.

    Use for 'take me to quality', 'where is the FAI screen?' and similar.
    Results contain registered paths, not fabricated destinations. This
    connector is local only, and routes may not open on another device.
    """
    return AxiomNavigationClient().find(query)


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    title="BEAN: View Axiom favorites",
    readOnlyHint=True, destructiveHint=False, idempotentHint=True,
    openWorldHint=False,
))
def bean_list_axiom_favorites() -> dict:
    """List actually saved Axiom Favorites. Does not infer from conversation."""
    return AxiomNavigationClient().list()


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    title="BEAN: Pin Axiom favorite",
    readOnlyHint=False, destructiveHint=False, idempotentHint=True,
    openWorldHint=False,
))
def bean_pin_axiom_favorite(module_key: str) -> dict:
    """Save a registered screen to the real Axiom Favorites menu.

    Use when the user directly asks to bookmark/pin/add to Favorites or accepts
    a concrete suggestion. First use bean_find_axiom_pages if the module key
    is unknown. Only say 'I added it' after this tool reports saved=true.
    """
    return AxiomNavigationClient().pin(module_key)


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    title="BEAN: Remove Axiom favorite",
    readOnlyHint=False, destructiveHint=False, idempotentHint=True,
    openWorldHint=False,
))
def bean_remove_axiom_favorite(module_key: str) -> dict:
    """Unpin a saved registered screen when the user asks to remove it."""
    return AxiomNavigationClient().remove(module_key)


def main() -> None:
    # Deliberately a separate service from the public read-only BEAN demo.
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1", port=8001,
        stateless_http=True, json_response=True,
        max_request_body_size=32768,
    )


if __name__ == "__main__":
    main()
