"""Validate navigation MCP discovery and read/write annotations."""
from __future__ import annotations

import asyncio

from integrations.chatgpt.axiom_server import mcp


def main():
    tools = asyncio.run(mcp.list_tools())
    expected = {
        "bean_find_axiom_pages": True,
        "bean_list_axiom_favorites": True,
        "bean_pin_axiom_favorite": False,
        "bean_remove_axiom_favorite": False,
    }
    found = {item.name: item for item in tools}
    if set(found) != set(expected):
        raise AssertionError("Navigation MCP tools missing or unexpected")
    for name, read_only in expected.items():
        tool = found[name]
        attrs = tool.annotations.model_dump(by_alias=True, exclude_none=True)
        if attrs.get("readOnlyHint") is not read_only:
            raise AssertionError(name + " has incorrect read-only annotation")
        if attrs.get("destructiveHint") is not False:
            raise AssertionError(name + " incorrectly marked destructive")
        if attrs.get("openWorldHint") is not False:
            raise AssertionError(name + " incorrectly declares public web access")
        if not tool.model_dump(by_alias=True).get("inputSchema"):
            raise AssertionError(name + " has no tool input schema")
    print("PASS: BEAN navigation MCP four actions, real write tools and honest metadata.")


if __name__ == "__main__":
    main()
