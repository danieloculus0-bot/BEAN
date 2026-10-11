"""Run real MCP SDK metadata checks before attempting external plugin submission."""
from __future__ import annotations

import asyncio

from integrations.chatgpt.server import mcp


def main() -> None:
    tools = asyncio.run(mcp.list_tools())
    expected = {
        "bean_audit_claim",
        "bean_compare_evidence",
        "bean_screen_proposal",
        "bean_demo_restart",
    }
    names = {tool.name for tool in tools}
    if names != expected:
        raise AssertionError(f"Unexpected public tool set: {names!r}")
    for tool in tools:
        annotations = tool.annotations
        if not annotations or annotations.readOnlyHint is not True:
            raise AssertionError(f"Tool {tool.name} is not marked read-only")
        if annotations.openWorldHint is not False:
            raise AssertionError(f"Tool {tool.name} incorrectly implies internet access")
        if annotations.destructiveHint is not False:
            raise AssertionError(f"Tool {tool.name} incorrectly marked destructive")
        if not tool.inputSchema:
            raise AssertionError(f"Tool {tool.name} has no input schema")
    print("PASS BEAN MCP tool registration, four JSON schemas, read-only annotations.")


if __name__ == "__main__":
    main()
