"""BEAN's public, bounded Model Context Protocol adapter.

Run from the BEAN repository root after installing the optional MCP SDK:
    python -m pip install "mcp>=2,<3" psutil
    python -m integrations.chatgpt.server

Default address is loopback 127.0.0.1:8000/mcp. A separate HTTPS deployment,
privacy policy, abuse protection, identity verification and directory review
are required before public publication. This demo intentionally has no private
user memory, filesystem access, browser search, credentials, effectors or writes.
"""
from __future__ import annotations

import os

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from bean.integration.public_plugin import (
    audit_claim,
    compare_evidence,
    demo_restart,
    screen_proposal,
)

mcp = MCPServer(
    "bean-evidence-companion",
    version="0.1.0",
    instructions=(
        "BEAN is a bounded evidence and memory engineering prototype. "
        "All submitted source statements are unverified. Never describe a "
        "heuristic verdict as factual verification or an MCP call as a "
        "persistent user memory. Review proposals without executing them."
    ),
)

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                            idempotentHint=True, openWorldHint=False)


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    title="BEAN: Audit a claim", readOnlyHint=True, destructiveHint=False,
    idempotentHint=True, openWorldHint=False,
))
def bean_audit_claim(
    claim: str,
    source_ref: str | None = None,
    evidence_refs: list[str] | None = None,
    confidence: float | None = None,
    falsification_test: str | None = None,
) -> dict:
    """Flag missing evidence, confidence, falsification paths and overclaims.

    BEAN applies its actual rule-based epistemic guard in a disposable local
    database. User-provided source identifiers are NOT authenticated. Even an
    approved heuristic result is NOT independent verification of a fact.
    Do not send credentials, customer records or confidential documents.
    """
    return audit_claim(claim, source_ref, evidence_refs, confidence, falsification_test)


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    title="BEAN: Compare conflicting statements", readOnlyHint=True,
    destructiveHint=False, idempotentHint=True, openWorldHint=False,
))
def bean_compare_evidence(question: str, observations: list[dict[str, str]]) -> dict:
    """Triage 1..12 user-supplied origin/statement pairs for disagreement.

    Example observations: [{"origin":"report A","statement":"machine ready"},
    {"origin":"report B","statement":"machine offline"}]. BEAN's actual
    evidence bridge keeps every claim UNVERIFIED even if sources agree.
    Never infer authenticated facts from the user's source labels.
    """
    return compare_evidence(question, observations)


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    title="BEAN: Screen a proposed plan", readOnlyHint=True,
    destructiveHint=False, idempotentHint=True, openWorldHint=False,
))
def bean_screen_proposal(
    summary: str,
    steps: list[str],
    evidence_refs: list[str] | None = None,
    uncertainties: list[str] | None = None,
) -> dict:
    """Run BEAN's real, limited proposal heuristics without performing actions.

    A pass is NOT a security certification, professional review, or permission
    to execute anything. Flagged claims should be checked by a human.
    """
    return screen_proposal(summary, steps, evidence_refs, uncertainties)


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    title="BEAN: Demonstrate durable memory", readOnlyHint=True,
    destructiveHint=False, idempotentHint=True, openWorldHint=False,
))
def bean_demo_restart() -> dict:
    """Demonstrate BEAN's real two-session SQLite event and proposal persistence.

    Uses fictional data and the mock reasoning adapter. The temporary DB is
    deleted, and there is NO remembered user state between plugin calls.
    """
    return demo_restart()


def main() -> None:
    port_raw = os.getenv("BEAN_MCP_PORT", "8000")
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ValueError("BEAN_MCP_PORT must be a valid TCP port") from exc
    if not 1 <= port <= 65535:
        raise ValueError("BEAN_MCP_PORT must be between 1 and 65535")
    host = os.getenv("BEAN_MCP_HOST", "127.0.0.1")
    if host not in ("127.0.0.1", "localhost", "0.0.0.0"):
        raise ValueError("Use a supported loopback or explicit deployment bind host")
    mcp.run(
        transport="streamable-http",
        host=host, port=port,
        stateless_http=True, json_response=True,
        max_request_body_size=32768,
    )


if __name__ == "__main__":
    main()
