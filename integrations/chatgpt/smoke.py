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
        advertised = annotations.model_dump(by_alias=True, exclude_none=True) if annotations else {}
        # SDK 2 uses snake_case Python fields and JSON aliases; ChatGPT
        # receives the serialized (camelCase) wire representation.
        if advertised.get("readOnlyHint") is not True:
            raise AssertionError(f"Tool {tool.name} is not advertised read-only: {advertised}")
        if advertised.get("openWorldHint") is not False:
            raise AssertionError(f"Tool {tool.name} incorrectly implies internet access: {advertised}")
        if advertised.get("destructiveHint") is not False:
            raise AssertionError(f"Tool {tool.name} incorrectly marked destructive: {advertised}")
        if not tool.model_dump(by_alias=True).get("inputSchema"):
            raise AssertionError(f"Tool {tool.name} has no input schema")
    print("PASS BEAN MCP tool registration, four JSON schemas, read-only annotations.")

    async def exercise_real_sdk():
        examples = [
            ("bean_audit_claim", {"claim": "The imaginary machine passed inspection"}),
            ("bean_compare_evidence", {"question": "What did the samples report?",
                "observations": [
                    {"origin": "Report A", "statement": "pass"},
                    {"origin": "Report B", "statement": "fail"},
                ]}),
            ("bean_screen_proposal", {"summary": "Read fictional log",
                "steps": ["Review source measurements"]}),
            ("bean_demo_restart", {}),
        ]
        for name, arguments in examples:
            result = await mcp.call_tool(name, arguments)
            if result.is_error:
                raise AssertionError(f"MCP actual tool {name} returned error: {result.content}")
            body = result.structured_content
            if not isinstance(body, dict) or "schema" not in body:
                raise AssertionError(f"MCP actual tool {name} lacks JSON schema result: {body}")
        print("PASS BEAN four real MCP SDK tool calls and structured results.")

    asyncio.run(exercise_real_sdk())


if __name__ == "__main__":
    main()
