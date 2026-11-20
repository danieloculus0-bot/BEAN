"""Actual SQLite plan ordering, failures and real native cognition; all synthetic."""
import json

import pytest

from bean.cognition.goal_state import (
    ActionType, ApprovalRequired, GoalProposal, GoalStateEngine, plan_proposal_id,
)
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.store import _local, get_store, init_store
from bean.runtime.goal_cycle import GoalCycle


@pytest.fixture
def core_db(tmp_path):
    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    path = tmp_path / "goals.sqlite"
    init_store(str(path))
    bootstrap_identity()
    session = begin_session()
    yield path, session
    get_store().close()


def step(name, action=ActionType.UPDATE_MODELS, priority=3, detail=None):
    return GoalProposal(name, action, "synthetic plan", priority,
                        ApprovalRequired.NONE, action_detail=detail)


def test_order_beats_priority_and_plan_resumes_without_replay(core_db):
    path, session = core_db
    templates = [step("first", priority=9), step("second", priority=1),
                 step("third", priority=1)]
    owner = GoalStateEngine()
    plan = owner.propose_plan(session, "restart-plan", templates)
    called = []
    cycle = GoalCycle({"update_models": lambda g: (
        called.append(g["goal_state"]) or {"status": "success"})})
    assert cycle.poll_due()[0]["proposal_id"] == plan[0].proposal_id
    get_store().close()
    init_store(str(path))
    other_session = begin_session()
    resumed = GoalCycle(cycle.actions)
    same = GoalStateEngine().propose_plan(other_session, "restart-plan", templates)
    assert [p.proposal_id for p in same] == [p.proposal_id for p in plan]
    assert same[0].status == "completed"
    assert len(resumed.poll_due(max_goals=5)) == 2
    assert called == ["first", "second", "third"]
    assert resumed.plan_status("restart-plan")["status"] == "completed"
    assert resumed.poll_due() == []


@pytest.mark.parametrize("outcome,status", [
    ("failed", "failed"), ("unknown", "needs_review"),
    ("unverified", "needs_evidence"), ("interrupted", "needs_review"),
])
def test_unresolved_predecessor_never_releases_dependents(core_db, outcome, status):
    path, session = core_db
    plan = GoalStateEngine().propose_plan(session, "blocked", [step("one"), step("two")])
    cycle = GoalCycle({"update_models": lambda _: {"status": outcome}})
    if outcome == "interrupted":
        assert cycle._claim()["proposal_id"] == plan[0].proposal_id
    else:
        assert len(cycle.poll_due(max_goals=5)) == 1
    get_store().close()
    init_store(str(path))
    reopened = GoalCycle({"update_models": lambda _: pytest.fail("unresolved replay")})
    assert reopened.recover_interrupted() == (outcome == "interrupted")
    assert reopened.poll_due(max_goals=5) == []
    progress = reopened.plan_status("blocked")
    assert progress["status"] == status
    assert progress["steps"][1]["status"] == "pending"


def test_immutable_plan_cannot_reset_history_or_partially_insert(core_db):
    _, session = core_db
    owner = GoalStateEngine()
    owner.propose_plan(session, "immutable", [step("one"), step("two")])
    with pytest.raises(ValueError, match="immutable"):
        owner.propose_plan(session, "immutable", [step("one"), step("changed")])
    assert get_store().fetchone("SELECT count(*) n FROM cognition_goal_proposals")["n"] == 2
    with pytest.raises(ValueError):
        owner.propose_plan(session, "invalid", [step("one"), step("two", detail={"x": float("nan")})])
    assert get_store().fetchone("SELECT count(*) n FROM cognition_goal_proposals")["n"] == 2
    get_store().execute("DELETE FROM cognition_goal_proposals WHERE proposal_id=?",
                        (plan_proposal_id("immutable", 1),))
    get_store().commit()
    with pytest.raises(ValueError, match="incomplete"):
        owner.propose_plan(session, "immutable", [step("one"), step("two")])


def test_waiting_plans_do_not_starve_ready_goals_and_missing_step_is_unknown(core_db):
    _, session = core_db
    owner = GoalStateEngine()
    for n in range(105):
        owner.propose_plan(session, f"wait-{n}", [
            step("unsupported", ActionType.PRACTICE_SKILL), step("blocked", priority=1)])
    runnable = step("available", priority=9)
    owner._persist(runnable, session)
    cycle = GoalCycle({"update_models": lambda _: {"status": "success"}})
    assert cycle.poll_due()[0]["proposal_id"] == runnable.proposal_id
    assert cycle.plan_status("not-created")["status"] == "unknown"
    get_store().execute("DELETE FROM cognition_goal_proposals WHERE proposal_id=?",
                        (plan_proposal_id("wait-0", 0),))
    get_store().commit()
    assert cycle.plan_status("wait-0")["status"] == "unknown"
    assert cycle.poll_due() == []


@pytest.mark.parametrize("bad", ["", "with space", "🫘", "a" * 101, None])
def test_invalid_plan_ids_rejected(core_db, bad):
    with pytest.raises(ValueError):
        GoalStateEngine().propose_plan(core_db[1], bad, [step("one")])


def test_transaction_failure_rolls_back_earlier_steps(core_db):
    import sqlite3
    broken = step("cannot-persist")
    broken.priority = None  # Violate the existing NOT NULL schema on step 2.
    with pytest.raises(sqlite3.IntegrityError):
        GoalStateEngine().propose_plan(core_db[1], "rollback", [step("first"), broken])
    assert get_store().fetchone("SELECT count(*) n FROM cognition_goal_proposals")["n"] == 0


def test_invalid_plan_metadata_and_approval_do_not_release_actions(core_db):
    _, session = core_db
    owner = GoalStateEngine()
    first = step("requires-existing-approval")
    first.approval_required = ApprovalRequired.HARDWARE
    owner.propose_plan(session, "approval", [first, step("dependent")])
    cycle = GoalCycle({"update_models": lambda _: pytest.fail("approval bypass")})
    assert cycle.poll_due() == []
    assert cycle.plan_status("approval")["status"] == "pending"
    plan = owner.propose_plan(session, "damaged", [step("one"), step("two")])
    value = dict(plan[0].action_detail)
    value["goal_plan"] = {"schema": "unsupported"}
    get_store().execute("UPDATE cognition_goal_proposals SET action_detail=? WHERE proposal_id=?",
                        (json.dumps(value), plan[0].proposal_id))
    get_store().commit()
    assert cycle.plan_status("damaged")["status"] == "unknown"
    assert cycle.poll_due(max_goals=5) == []


def test_real_core_learning_prediction_feedback_then_restart_adaptation(tmp_path):
    import hashlib
    from bean.evaluation.goal_plan_cycle import run_probe

    report = run_probe(tmp_path / "probe")
    assert report["first_session"] != report["resumed_session"]
    assert [s["status"] for s in report["first_progress"]["steps"]] == [
        "completed", "pending", "pending"]
    assert report["progress"]["status"] == "completed"
    assert report["same_plan_ids"] and report["no_replay"]
    assert report["continued_steps"] == 2
    assert report["recovered_interrupted"] == 0
    assert [t["stage"] for t in report["trace"]] == [
        "retrieval_hypothesis_memory", "action_evaluation", "feedback_memory_update"]
    prediction = report["trace"][1]
    assert prediction["prediction_matches_expected"] is False
    assert prediction["observed_answer"] == "KJL"
    assert prediction["independent_outcome_verified"] is False
    assert report["trace"][2]["receipt_id"] == prediction["core_receipt_id"]
    assert report["trace"][2]["matched"] is True
    assert report["controls"]["cold_before"]["status"] == "abstain"
    assert report["controls"]["cold_later"]["status"] == "abstain"
    assert report["controls"]["later_core"]["answer"] == "NOM"
    assert report["controls"]["candidate_advantage_over_fixed_rule"] == 0
    assert report["general_learning_advantage_proven"] is False
    assert len(report["runs"]) == 3
    for row in report["runs"]:
        decision = json.loads(row["decision_json"])
        assert decision["goal_plan"]["id"] == "cognition-probe"
    assert [r["kind"] for r in report["reasoning_journal"]].count("feedback") == 1
    events = [e for e in report["canonical_events"] if e["subtype"] == "autonomous_goal_cycle"]
    assert len(events) == 3
    by_run = {r["run_id"]: r for r in report["runs"]}
    for event in events:
        receipt = json.loads(event["data"])
        result = by_run[receipt["run_id"]]["result_json"]
        assert receipt["result_sha256"] == hashlib.sha256(result.encode("utf-8")).hexdigest()
    saved = json.loads((tmp_path / "probe/report.json").read_text())
    digest = saved.pop("receipt_sha256")
    encoded = json.dumps(saved, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert hashlib.sha256(encoded.encode("utf-8")).hexdigest() == digest
    with pytest.raises(FileExistsError):
        run_probe(tmp_path / "probe")
