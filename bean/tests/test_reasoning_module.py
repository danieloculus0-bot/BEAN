"""Brain 0.11 reasoning module tests."""

from __future__ import annotations

import sqlite3

from bean.reasoning import get_provider
from bean.reasoning.action_validator import validate_action_candidate
from bean.reasoning.proposal import ReasoningProposal, decide_action_candidate, get_pending_candidates, get_proposal, init_reasoning_schema, persist_proposal
from bean.reasoning.reasoning_engine import run_reasoning_cycle
from bean.reasoning.providers.stub_provider import StubProvider
from bean.speculation import init_speculation

SESSION = "reasoning_test_session"


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    CREATE TABLE events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_uuid TEXT,
        event_type TEXT,
        subtype TEXT,
        summary TEXT,
        data TEXT,
        source TEXT,
        severity TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    init_reasoning_schema(conn)
    init_speculation(conn)
    return conn


def test_stub_provider_fallback_without_key():
    provider = get_provider(force_stub=True)
    assert isinstance(provider, StubProvider)


def test_validate_unknown_action_type_rejected():
    result = validate_action_candidate({"action_type": "do_magic", "rationale": "bad", "risk_level": "low"})
    assert result["valid"] is False


def test_motion_candidate_cannot_validate_for_execution():
    result = validate_action_candidate({"action_type": "propose_motion", "rationale": "move", "risk_level": "high", "payload": {}})
    assert result["valid"] is False
    assert result["candidate"]["motion_enabled"] is False


def test_persist_proposal_and_candidates():
    conn = make_conn()
    proposal = ReasoningProposal(
        session_uuid=SESSION,
        source_context={"motion_enabled": False},
        reasoning_text="Reasoning without action.",
        summary="Safe proposal.",
        confidence=0.4,
        provider="test",
        action_candidates=[{"action_type": "defer", "rationale": "Wait.", "payload": {}, "risk_level": "low"}],
        referenced_hypothesis_ids=["hyp_test"],
    )
    pid = persist_proposal(conn, proposal)
    fetched = get_proposal(conn, pid)
    assert fetched["referenced_hypothesis_ids"] == ["hyp_test"]
    assert len(get_pending_candidates(conn)) == 1


def test_decide_candidate_does_not_execute():
    conn = make_conn()
    proposal = ReasoningProposal(
        session_uuid=SESSION,
        source_context={},
        reasoning_text="Reasoning only.",
        summary="Candidate only.",
        action_candidates=[{"candidate_id": "cand_x", "action_type": "defer", "rationale": "No action.", "payload": {}, "risk_level": "low"}],
    )
    persist_proposal(conn, proposal)
    result = decide_action_candidate(conn, "cand_x", "accepted", "tester")
    assert result["executed"] is False
    assert result["motion_enabled"] is False


def test_reasoning_cycle_persists_stub_output():
    conn = make_conn()
    provider = StubProvider()
    result = run_reasoning_cycle(SESSION, provider, instruction="test", conn=conn)
    assert result["ok"] is True
    assert result["executed"] is False
    assert result["motion_enabled"] is False
    assert get_proposal(conn, result["proposal_id"]) is not None


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    failed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"PASS {name}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
            import traceback
            traceback.print_exc()
    print(f"{len(tests) - failed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
