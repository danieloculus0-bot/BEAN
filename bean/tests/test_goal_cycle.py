"""Synthetic offline regression for native BEAN autonomous goal execution."""
import json
import pytest
from bean.cognition.goal_state import ActionType, ApprovalRequired, GoalProposal, GoalStateEngine
from bean.memory.store import _local, get_store, init_store
from bean.runtime.goal_cycle import GoalCycle
from bean.runtime.tick_handlers import build_default_handlers


@pytest.fixture
def memory(tmp_path):
    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    init_store(str(tmp_path / "goal_cycle.sqlite"))
    owner = GoalStateEngine()
    def propose(action=ActionType.UPDATE_MODELS, priority=3,
                approval=ApprovalRequired.NONE, goal="refresh"):
        item = GoalProposal(goal, action, "synthetic curiosity", priority, approval)
        owner._persist(item, "synthetic-session")
        return item
    yield propose
    get_store().close()


def test_executes_goal_and_recovers_memory(memory):
    item = memory()
    calls = []
    recorded = []
    cycle = GoalCycle({"update_models": lambda g: calls.append(g["goal_state"]) or
                       {"status": "success", "updates": 1}},
                      event_sink=recorded.append)
    result = cycle.poll_due()
    assert result[0]["status"] == "success"
    assert recorded == result and calls == ["refresh"]
    restarted = GoalCycle({"update_models": lambda g: calls.append("replayed")})
    assert restarted.recover_interrupted() == 0
    assert restarted.poll_due() == []
    assert restarted.history()[0]["proposal_id"] == item.proposal_id
    assert calls == ["refresh"]


def test_no_approval_or_missing_capability_remains_pending(memory):
    hardware = memory(ActionType.REDUCE_LOAD, 1, ApprovalRequired.HARDWARE)
    supervisor = memory(ActionType.UPDATE_MODELS, 1, ApprovalRequired.SUPERVISOR)
    missing = memory(ActionType.RUN_EXPERIMENT, 1, ApprovalRequired.NONE)
    cycle = GoalCycle({"update_models": lambda _: pytest.fail("unauthorized")})
    assert cycle.poll_due() == []
    states = get_store().fetchall(
        "SELECT status FROM cognition_goal_proposals ORDER BY id")
    assert [s["status"] for s in states] == ["pending"] * 3
    assert all(x.proposal_id for x in (hardware,supervisor,missing))


def test_real_registered_digital_experiment(memory):
    item = memory(ActionType.RUN_EXPERIMENT, goal="investigate")
    seen = []
    cycle = GoalCycle({"run_experiment": lambda g: seen.append(g["proposal_id"]) or
                       {"status": "verified", "synthetic": True}})
    assert cycle.poll_due()[0]["status"] == "success"
    assert seen == [item.proposal_id]


@pytest.mark.parametrize("value,expected,final", [
    ({"status": "unknown"}, "unknown", "needs_review"),
    ({"status": "unverified"}, "n/a", "needs_evidence"),
    ({"status": "failed"}, "failed", "failed"),
    ({"status": "verified"}, "success", "completed"),
])
def test_truthful_outcome_states(memory, value, expected, final):
    item = memory()
    cycle = GoalCycle({"update_models": lambda _: value})
    assert cycle.poll_due()[0]["status"] == expected
    assert get_store().fetchone(
        "SELECT status FROM cognition_goal_proposals WHERE proposal_id=?",
        (item.proposal_id,))["status"] == final


def test_interruption_never_replays_effect(memory):
    item = memory()
    effects = []
    cycle = GoalCycle({"update_models": lambda _: effects.append("one")})
    claimed = cycle._claim()
    assert claimed["proposal_id"] == item.proposal_id
    cycle.actions["update_models"](claimed)
    recovered = GoalCycle({"update_models": lambda _: effects.append("two")})
    assert recovered.recover_interrupted() == 1
    assert recovered.poll_due() == []
    assert recovered.history()[0]["state"] == "unknown"
    assert effects == ["one"]


def test_failed_action_is_recorded_not_hidden(memory):
    memory()
    def broken(_):
        raise RuntimeError("synthetic fault")
    cycle = GoalCycle({"update_models": broken})
    assert cycle.poll_due()[0]["status"] == "failed"
    assert cycle.poll_due() == []
    assert "synthetic fault" in cycle.history()[0]["error"]


def test_novelty_changes_selection_using_persisted_history(memory):
    memory(ActionType.UPDATE_MODELS, goal="first")
    cycle = GoalCycle({"update_models": lambda _: {"status": "success"},
                       "run_reflection": lambda _: {"status": "success"}})
    cycle.poll_due()
    later = memory(ActionType.UPDATE_MODELS, goal="later")
    novel = memory(ActionType.RUN_REFLECTION, goal="novel")
    choice = cycle.poll_due()[0]
    assert choice["proposal_id"] == novel.proposal_id
    assert json.loads(cycle.history()[0]["decision_json"])["prior_attempts"] == 0
    assert cycle.poll_due()[0]["proposal_id"] == later.proposal_id


def test_tick_scheduler_runs_native_goals(memory):
    item = memory()
    seen = []
    cycle = GoalCycle({"update_models": lambda _: seen.append("done") or
                       {"status": "success"}})
    handlers = build_default_handlers(goal_cycle=cycle)
    handlers.run_due(0, "synthetic-session", {})
    assert seen == ["done"]
    assert item.proposal_id in [r["proposal_id"] for r in cycle.history()]
