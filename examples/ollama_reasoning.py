#!/usr/bin/env python3
"""Windows-friendly live Ollama -> BEAN persistent proposal smoke.

Requires an explicitly configured BEAN_DB_PATH and running local Ollama.
The model cannot execute commands or approve its own proposal.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from bean.integration import BeanReasoningLayer


def main() -> None:
    db_path = os.environ.get("BEAN_DB_PATH")
    if not db_path:
        raise SystemExit("Set BEAN_DB_PATH to the intended persistent SQLite file before running.")
    target = Path(db_path)
    if not target.parent.exists():
        raise SystemExit("BEAN_DB_PATH parent does not exist; refusing to create unexpected folders.")

    with BeanReasoningLayer(str(target)) as bean:
        receipt = bean.observe_and_reason(
            "Windows operator requested a real local Ollama reasoning connection test.",
            data={"source": "local_operator", "kind": "provider_smoke"},
            adapter_name="ollama",
        )
        proposal = bean.store.fetchone(
            "SELECT summary, confidence, status, risk_flags_json FROM reasoning_proposals "
            "WHERE proposal_id=?",
            (receipt["proposal_id"],),
        )
        response = bean.store.fetchone(
            "SELECT parse_success FROM reasoning_responses WHERE response_id=?",
            (receipt["response_id"],),
        )
        risk_flags = json.loads(proposal["risk_flags_json"])
        passed = bool(response["parse_success"]) and "provider_unavailable" not in risk_flags
        print(json.dumps({
            "local_ollama_structured_reasoning": "PASS" if passed else "FAILED_OR_UNAVAILABLE",
            "database": str(target),
            "proposal_id": receipt["proposal_id"],
            "proposal_status": proposal["status"],
            "summary": proposal["summary"],
            "confidence": proposal["confidence"],
            "risk_flags": risk_flags,
            "supervisor_review_required": receipt["requires_supervisor_review"],
            "command_executed": False,
        }, indent=2))
        if not passed:
            raise SystemExit("The model did not produce a validated structured response.")


if __name__ == "__main__":
    main()
