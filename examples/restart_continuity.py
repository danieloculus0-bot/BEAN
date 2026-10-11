#!/usr/bin/env python3
"""A real two-session BEAN SQLite persistence demonstration.

Reopens the same temporary SQLite database after a clean shutdown to verify
that recorded event and review-required proposal survive. Uses the mock
provider; no network, real model, customer data, tools, or physical effects.

Run: python -m examples.restart_continuity
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from bean.integration import BeanReasoningLayer
from bean.memory.session import get_continuity_context
from bean.memory.store import get_store


def run_demo() -> dict:
    with tempfile.TemporaryDirectory(prefix="bean-restart-proof-") as tmp:
        database = Path(tmp) / "reopen.sqlite3"
        with BeanReasoningLayer(str(database)) as first:
            first_session = first.session_uuid
            reply = first.observe_and_reason(
                "An offline fictional quality observation needs human review.",
                data={"source": "synthetic_example", "measurement": None,
                      "verified": False, "customer_data": False},
                subtype="public_restart_demo",
                adapter_name="mock",
            )
            event_id = reply["event_id"]
            proposal_id = reply["proposal_id"]
            if not proposal_id or not reply["requires_supervisor_review"]:
                raise AssertionError("Mock reasoning did not retain review boundary")
            if reply["motion_command_generated"]:
                raise AssertionError("Demo unexpectedly generated a motion command")

        # A new BEAN lifecycle opens the *same* durable database.
        with BeanReasoningLayer(str(database)) as second:
            second_session = second.session_uuid
            if first_session == second_session:
                raise AssertionError("Second lifecycle did not start a distinct session")
            continuity = get_continuity_context(limit=2)
            event = get_store().fetchone(
                "SELECT id,session_uuid FROM events WHERE id=?", (event_id,)
            )
            proposal = get_store().fetchone(
                "SELECT proposal_id,session_uuid,status FROM reasoning_proposals WHERE proposal_id=?",
                (proposal_id,),
            )
            prior_session = get_store().fetchone(
                "SELECT shutdown_time FROM sessions WHERE session_uuid=?",
                (first_session,),
            )
            if not event or event["session_uuid"] != first_session:
                raise AssertionError("Event did not persist after BEAN restart")
            if not proposal or proposal["session_uuid"] != first_session:
                raise AssertionError("Stored proposal did not persist after BEAN restart")
            if not prior_session or not prior_session["shutdown_time"]:
                raise AssertionError("First BEAN session did not close cleanly")
            if continuity["total_boots"] < 2:
                raise AssertionError("Session count did not persist across restart")
            if proposal["status"] != "pending_review":
                raise AssertionError("Unreviewed proposal unexpectedly changed state")

            result = {
                "schema": "bean.public.restart_proof.v1",
                "provider": "mock_fixture_not_live_llm",
                "real_sqlite_restart_test": True,
                "distinct_sessions": True,
                "boot_records_at_least": continuity["total_boots"],
                "persisted_event_found": True,
                "persisted_review_proposal_found": True,
                "proposal_status_after_restart": proposal["status"],
                "source_authentication": "synthetic_only",
                "effectors_called": False,
                "external_requests": False,
                "database_lifetime": "temporary_local_only",
            }
        return result


def main() -> None:
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
    print("BEAN restart proof passed. Temporary local files cleaned up.")


if __name__ == "__main__":
    main()
