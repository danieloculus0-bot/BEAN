"""Live loopback MCP handshake through BEAN's authenticated ASGI gateway.

Runs only against a temporary local subprocess; no public host, tokens or
private state. Tests reject unauthorized clients and discover real BEAN tools.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SECRET = "local-ci-token-" + "z" * 48
EXPECTED = {
    "bean_audit_claim",
    "bean_compare_evidence",
    "bean_screen_proposal",
    "bean_demo_restart",
}


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def smoke(port):
    url = f"http://127.0.0.1:{port}/mcp"
    async with httpx.AsyncClient() as client:
        r = await client.get(f"http://127.0.0.1:{port}/health")
        assert r.status_code == 200 and r.text == "ok", (r.status_code, r.text)
        r = await client.post(url, json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "bean-auth-smoke", "version": "1"},
            },
        })
        assert r.status_code == 401, r.status_code

    async with httpx.AsyncClient(headers={
        "Authorization": "Bearer " + SECRET,
    }) as client:
        async with streamable_http_client(url, http_client=client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                found = {tool.name for tool in tools.tools}
                assert found == EXPECTED, found
                result = await session.call_tool("bean_audit_claim", {
                    "claim": "Fictional gasket meets the drawing tolerance",
                })
                assert not result.is_error, result.content
                assert result.structured_content["schema"] == "bean.plugin.claim_audit.v1"
    print("PASS authenticated MCP HTTP initialize, tools/list, tool call, 401 and health.")


def main():
    port = free_port()
    env = dict(os.environ, BEAN_MCP_API_KEY=SECRET)
    process = subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "integrations.chatgpt.perplexity_remote:app",
        "--host", "127.0.0.1", "--port", str(port), "--no-access-log",
    ], cwd=Path(__file__).resolve().parents[2], env=env,
       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("MCP gateway exited before readiness")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.25)
        else:
            raise TimeoutError("BEAN authenticated gateway did not start")
        asyncio.run(smoke(port))
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


if __name__ == "__main__":
    main()
