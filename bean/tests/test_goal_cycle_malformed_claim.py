"""Regression: malformed persisted goals cannot strand native GoalCycle claims."""
from bean.cognition.goal_state import ActionType, ApprovalRequired, GoalProposal, GoalStateEngine
from bean.memory.store import _local, get_store, init_store
from bean.runtime.goal_cycle import GoalCycle


def test_malformed_goal_is_skipped_and_valid_goal_executes(tmp_path):
    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    init_store(str(tmp_path / "goal.sqlite"))
    try:
        engine = GoalStateEngine()
        broken = GoalProposal("broken", ActionType.UPDATE_MODELS, "test", 1, ApprovalRequired.NONE)
        valid = GoalProposal("valid", ActionType.UPDATE_MODELS, "test", 2, ApprovalRequired.NONE)
        engine._persist(broken, "session")
        engine._persist(valid, "session")
        store = get_store()
        store._conn().execute(
            "UPDATE cognition_goal_proposals SET action_detail=? WHERE proposal_id=?",
            ('{invalid json', broken.proposal_id),
        )
        store.commit()
        calls = []
        cycle = GoalCycle({"update_models": lambda goal: calls.append(goal["proposal_id"]) or {"status": "success"}})
        receipts = cycle.poll_due(max_goals=2)
        assert [r["proposal_id"] for r in receipts] == [valid.proposal_id]
        assert calls == [valid.proposal_id]
        assert store.fetchone("SELECT status FROM cognition_goal_proposals WHERE proposal_id=?", (broken.proposal_id,))["status"] == "pending"
        assert not store.fetchone("SELECT run_id FROM bean_goal_runs WHERE proposal_id=?", (broken.proposal_id,))
        assert cycle.recover_interrupted() == 0
    finally:
        get_store().close()
