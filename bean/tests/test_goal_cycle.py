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


@pytest.mark.parametrize("outcome", [
    "pending", "success", "failed", "unknown", "unverified", "interrupted",
])
def test_unchanged_question_does_not_repeat_after_attempt_or_restart(memory, outcome):
    from bean.memory.identity import bootstrap_identity
    from bean.memory.session import begin_session

    bootstrap_identity()
    session = begin_session()
    engine = GoalStateEngine()
    question = {
        "id": 77, "question": "Does the synthetic sum rule predict the outcome?",
        "context": {
            "schema": "bean.cognition.experiment.v1", "capability": "sum",
            "inputs": {"values": [2, 3]}, "expected_output": {"sum": 6},
        },
    }
    original = engine.propose(session, [], [question])[0]
    cycle = GoalCycle({"run_experiment": lambda _: {"status": outcome}})
    if outcome == "interrupted":
        assert cycle._claim()["proposal_id"] == original.proposal_id
    elif outcome != "pending":
        assert len(cycle.poll_due()) == 1
    assert engine.propose(session, [], [question]) == []

    path = get_store().db_path
    get_store().close()
    init_store(path)
    new_session = begin_session()
    restarted = GoalCycle({"run_experiment": lambda _: pytest.fail("replayed")})
    assert restarted.recover_interrupted() == (outcome == "interrupted")
    assert GoalStateEngine().propose(new_session, [], [question]) == []
    rows = get_store().fetchall("SELECT proposal_id FROM cognition_goal_proposals")
    assert [row["proposal_id"] for row in rows] == [original.proposal_id]

    # A corrected prediction is a new experiment, retaining the failed path.
    question["context"]["expected_output"] = {"sum": 5}
    revised = GoalStateEngine().propose(new_session, [], [question])
    assert len(revised) == 1
    assert revised[0].proposal_id != original.proposal_id


def test_goal_outcome_event_links_to_exact_persisted_result_after_restart(memory):
    """The event receipt authenticates stored bytes, not an invented success."""
    import hashlib

    item = memory()
    emitted = []
    outcome = {"status": "verified", "observations": [1, 2, 3]}
    cycle = GoalCycle({"update_models": lambda _: outcome},
                      event_sink=emitted.append)
    result = cycle.poll_due()[0]
    assert result["status"] == "success"
    assert emitted == [result]
    stored = get_store().fetchone(
        "SELECT result_json FROM bean_goal_runs WHERE proposal_id=?",
        (item.proposal_id,))["result_json"]
    expected_digest = hashlib.sha256(stored.encode("utf-8")).hexdigest()
    assert result["result_sha256"] == expected_digest
    assert json.loads(stored) == outcome

    path = get_store().db_path
    get_store().close()
    init_store(path)
    restarted = GoalCycle({"update_models": lambda _: pytest.fail("replayed")})
    assert restarted.poll_due() == []
    persisted = restarted.history()[0]["result_json"]
    assert hashlib.sha256(persisted.encode("utf-8")).hexdigest() == expected_digest


def test_failed_goal_has_no_fabricated_result_digest(memory):
    memory()
    emitted = []
    def broken(_):
        raise RuntimeError("synthetic failed operation")
    result = GoalCycle({"update_models": broken},
                       event_sink=emitted.append).poll_due()[0]
    assert result["status"] == "failed"
    assert result["result_sha256"] is None
    assert emitted == [result]


def test_large_goal_outcome_is_parseable_evidence_gap_after_restart(memory):
    """A bounded durable receipt must not contain half a JSON document."""
    import hashlib

    item = memory()
    original = {"status": "verified", "data": "🫘" * 3000}
    encoded = json.dumps(original, default=str, ensure_ascii=False)
    receipt = GoalCycle({"update_models": lambda _: original}).poll_due()[0]
    assert receipt["status"] == "success"
    assert receipt["result_truncated"] is True

    stored = get_store().fetchone(
        "SELECT result_json FROM bean_goal_runs WHERE proposal_id=?",
        (item.proposal_id,))["result_json"]
    envelope = json.loads(stored)
    assert envelope["schema"] == "bean.goal.result_truncated.v1"
    assert envelope["truncated"] is True
    assert envelope["original_utf8_bytes"] == len(encoded.encode("utf-8"))
    assert envelope["original_sha256"] == hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    assert len(stored.encode("utf-8")) <= 8192
    assert receipt["result_sha256"] == hashlib.sha256(stored.encode("utf-8")).hexdigest()

    path = get_store().db_path
    get_store().close()
    init_store(path)
    restarted = GoalCycle({"update_models": lambda _: pytest.fail("replayed")})
    assert restarted.poll_due() == []
    assert json.loads(restarted.history()[0]["result_json"]) == envelope


def test_small_goal_result_retains_exact_json_and_not_truncated(memory):
    memory()
    original = {"status": "verified", "evidence": [1, 2]}
    receipt = GoalCycle({"update_models": lambda _: original}).poll_due()[0]
    assert receipt["result_truncated"] is False
    assert json.loads(GoalCycle({"update_models": lambda _: None}).history()[0]["result_json"]) == original


def test_failed_experience_can_change_goal_choice_without_erasing_priority(memory):
    """Observed failures can change choice, without implying perfect decisions."""
    seen = []
    def fail(_):
        seen.append("failed")
        return {"status": "failed"}
    def novel(_):
        seen.append("novel")
        return {"status": "success"}

    cycle = GoalCycle({"update_models": fail, "run_reflection": novel})
    # Before experience, a fresh priority-1 action outranks priority-2.
    first = memory(ActionType.UPDATE_MODELS, priority=1, goal="initial")
    second = memory(ActionType.RUN_REFLECTION, priority=2, goal="alternative")
    assert cycle.poll_due()[0]["proposal_id"] == first.proposal_id
    assert seen == ["failed"]
    # Resolve the initial alternative so it cannot preempt training attempts.
    assert cycle.poll_due()[0]["proposal_id"] == second.proposal_id
    seen.clear()

    # Accumulate real persisted failed action receipts, not a fabricated score.
    for index in range(19):
        item = memory(ActionType.UPDATE_MODELS, priority=1, goal=f"retry-{index}")
        assert cycle.poll_due()[0]["proposal_id"] == item.proposal_id
    assert len(seen) == 19 and all(x == "failed" for x in seen)

    # Reopen the existing SQLite store to prove outcome-dependent selection
    # survives process-local state loss. Neither action has been replayed.
    path = get_store().db_path
    get_store().close()
    init_store(path)
    restarted = GoalCycle({"update_models": fail, "run_reflection": novel})
    higher_priority = memory(ActionType.UPDATE_MODELS, priority=1, goal="after-feedback")
    alternative = memory(ActionType.RUN_REFLECTION, priority=2, goal="new-alternative")
    selected = restarted.poll_due()[0]
    assert selected["proposal_id"] == alternative.proposal_id
    assert selected["decision"]["policy"] == "priority_novelty_observed_outcomes_v2"
    assert selected["decision"]["prior_attempts"] == 1
    assert selected["status"] == "success"
    assert seen[-1] == "novel"
    assert get_store().fetchone(
        "SELECT status FROM cognition_goal_proposals WHERE proposal_id=?",
        (higher_priority.proposal_id,)
    )["status"] == "pending"


def test_unknown_outcomes_are_not_counted_as_success_or_failure(memory):
    cycle = GoalCycle({"update_models": lambda _: {"status": "unknown"}})
    memory(ActionType.UPDATE_MODELS, priority=2, goal="unresolved")
    assert cycle.poll_due()[0]["status"] == "unknown"
    memory(ActionType.UPDATE_MODELS, priority=2, goal="later")
    receipt = cycle.poll_due()[0]
    assert receipt["decision"]["prior_attempts"] == 1
    assert receipt["decision"]["observed_successes"] == 0
    assert receipt["decision"]["observed_failures"] == 0
    assert receipt["decision"]["unknown_not_rewarded"] is True
