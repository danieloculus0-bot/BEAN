"""Real loopback Streamable HTTP MCP handshake and tool calls (CI only).

Starts BEAN MCP in a separate subprocess, uses the official Python MCP client,
and stops the subprocess. Never opens the host beyond loopback.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _exercise(port: int) -> None:
    async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            available = await session.list_tools()
            names = {tool.name for tool in available.tools}
            assert names == {
                "bean_audit_claim", "bean_compare_evidence",
                "bean_screen_proposal", "bean_demo_restart",
            }, names
            a = await session.call_tool("bean_audit_claim",
                                        {"claim": "Fictional warehouse roof is sound"})
            assert not a.is_error, a.content
            assert a.structured_content["schema"] == "bean.plugin.claim_audit.v1"
            e = await session.call_tool("bean_compare_evidence", {
                "question": "Does the fictional sensor pass?",
                "observations": [
                    {"origin": "Report A", "statement": "pass"},
                    {"origin": "Report B", "statement": "fail"},
                ],
            })
            assert not e.is_error, e.content
            assert e.structured_content["verified_independent_origins"] == 0
            assert e.structured_content["reported_positions_conflict"] is True
            p = await session.call_tool("bean_screen_proposal", {
                "summary": "Inspect fictional part",
                "steps": ["Review a synthetic measurement"],
            })
            assert not p.is_error, p.content
            assert p.structured_content["execution_permission"] == "none"
            m = await session.call_tool("bean_demo_restart", {})
            assert not m.is_error, m.content
            assert m.structured_content["core_restart_proof"]["persisted_review_proposal_found"]
            print("PASS BEAN real HTTP handshake, tools/list, four tools/call, evidence boundaries.")


def main() -> None:
    port = _free_port()
    env = os.environ.copy()
    env["BEAN_MCP_HOST"] = "127.0.0.1"
    env["BEAN_MCP_PORT"] = str(port)
    repo = Path(__file__).resolve().parents[2]
    process = subprocess.Popen(
        [sys.executable, "-m", "integrations.chatgpt.server"],
        env=env, cwd=repo,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("BEAN MCP server exited before HTTP readiness")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                    break
            except OSError:
                time.sleep(0.25)
        else:
            raise TimeoutError("BEAN MCP HTTP endpoint never became reachable")
        asyncio.run(_exercise(port))
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            _, errors = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            _, errors = process.communicate(timeout=5)
        if process.returncode not in (0, -15, 1):
            # Windows terminate return codes differ from POSIX SIGTERM.
            pass
        # Don't print server logs on success; calls may contain user content.
        # CI uses synthetic inputs, so a failure can be debugged from the
        # client exception and the job's isolated stdout, not source text.


if __name__ == "__main__":
    main()
