"""Brain 0.14 self-optimization governor smoke tests."""

from __future__ import annotations

import sqlite3

from bean.optimization import init_self_optimization


def make_governor():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return init_self_optimization(conn)


def proposal_args():
    return {
        "session_uuid": "session-test",
        "title": "Compare mobile base configurations",
        "problem_statement": "The future body configuration has not been selected.",
        "proposed_change": "Compare a four-wheel rocker-bogie base against articulated legs in simulation.",
        "target_layer": "embodiment",
        "proposal_type": "experiment",
        "expected_benefit": "Select a body with evidence instead of preference.",
        "expected_cost": "Simulation time and prototype design effort.",
        "risk_level": "medium",
        "validation_plan": "Score terrain access, energy use, stability, cost, and failure modes.",
        "rollback_plan": "Discard the experiment output and retain the current no-motion configuration.",
        "evidence_refs": ["event:terrain_requirement_001"],
        "alternatives": ["fixed wheeled base", "six-legged base"],
    }


def test_create_proposal_never_executes():
    governor = make_governor()
    proposal = governor.create_proposal(**proposal_args())
    assert proposal["proposal_id"].startswith("opt_")
    assert proposal["status"] == "proposed"
    assert proposal["execution_permission"] == "proposal_only"
    assert proposal["auto_executed"] is False
    assert proposal["motion_command_generated"] is False
    assert proposal["requires_supervisor_execution"] is True


def test_supervisor_can_approve_sandbox_without_auto_execution():
    governor = make_governor()
    proposal = governor.create_proposal(**proposal_args())
    reviewed = governor.review_proposal(
        proposal["proposal_id"],
        decision="approve_sandbox",
        reviewer="primary_developer",
        notes="Approved for simulation only. No physical output.",
    )
    assert reviewed["status"] == "approved_for_sandbox_test"
    assert reviewed["execution_permission"] == "sandbox_test_only"
    assert reviewed["auto_executed"] is False
    assert reviewed["motion_command_generated"] is False


def test_required_validation_and_rollback_are_enforced():
    governor = make_governor()
    args = proposal_args()
    args["rollback_plan"] = ""
    try:
        governor.create_proposal(**args)
        assert False
    except ValueError as exc:
        assert "rollback_plan" in str(exc)


def test_summary_counts_proposals():
    governor = make_governor()
    governor.create_proposal(**proposal_args())
    summary = governor.build_summary()
    assert summary["proposal_count"] == 1
    assert summary["by_status"]["proposed"] == 1
    assert summary["auto_execution_available"] is False
    assert summary["motion_enabled"] is False


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    failed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"PASS {name}")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            import traceback

            traceback.print_exc()
    raise SystemExit(1 if failed else 0)
