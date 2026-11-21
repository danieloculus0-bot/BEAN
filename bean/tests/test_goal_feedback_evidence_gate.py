"""Fail-closed independent feedback regression; synthetic SQLite, not learned transfer."""
import json

import pytest

from bean.cognition.goal_state import ActionType, ApprovalRequired, GoalProposal, GoalStateEngine
from bean.memory.store import _local, get_store, init_store
from bean.runtime.goal_cycle import GoalCycle


@pytest.fixture
def cycle(tmp_path):
    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    init_store(str(tmp_path / "feedback_gate.sqlite"))
    engine = GoalStateEngine()
    proposal = GoalProposal("synthetic", ActionType.UPDATE_MODELS, "synthetic evidence", 3, ApprovalRequired.NONE)
    engine._persist(proposal, "feedback-gate")
    instance = GoalCycle({"update_models": lambda _: {"status": "verified", "value": 3}})
    instance.poll_due()
    yield instance
    get_store().close()


@pytest.mark.parametrize("replacement", [None, "null", "{broken", json.dumps({
    "schema": "bean.goal.result_truncated.v1", "truncated": True,
    "original_sha256": "0" * 64})])
def test_incomplete_result_never_invokes_evaluator_or_writes_feedback(cycle, replacement):
    run_id = cycle.history()[0]["run_id"]
    get_store()._conn().execute(
        "UPDATE bean_goal_runs SET result_json=? WHERE run_id=?", (replacement, run_id))
    get_store().commit()
    calls = []
    with pytest.raises(ValueError, match="complete parseable result"):
        cycle.evaluate_run(run_id, lambda evidence: calls.append(evidence) or {"correct": True})
    assert calls == []
    # Schema initialization is allowed; invalid evidence must persist no verdict.
    assert get_store().fetchone(
        "SELECT COUNT(*) AS n FROM bean_goal_feedback"
    )["n"] == 0


def test_complete_result_is_scored_once_and_survives_restart(cycle):
    run_id = cycle.history()[0]["run_id"]
    original = cycle.history()[0]["result_json"]
    verdict = cycle.evaluate_run(run_id, lambda evidence: {
        "correct": evidence["result"]["value"] == 3, "evaluator": "synthetic-independent"})
    assert verdict["correct"] is True
    assert cycle.history()[0]["result_json"] == original
    with pytest.raises(Exception):
        cycle.evaluate_run(run_id, lambda _: {"correct": False})
    path = get_store().db_path
    get_store().close()
    init_store(path)
    recovered = GoalCycle({"update_models": lambda _: pytest.fail("must not replay")})
    assert recovered.poll_due() == []
    row = get_store().fetchone(
        "SELECT verdict_json FROM bean_goal_feedback WHERE run_id=?", (run_id,))
    assert json.loads(row["verdict_json"])["correct"] is True
