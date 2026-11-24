"""Native CLI reads actual durable plan results; never fabricates completion."""
import hashlib
import json
import sqlite3

import pytest

from bean.cognition.goal_state import PLAN_SCHEMA, plan_proposal_id
from bean.runtime.native_orchestration import CAPABILITY, read_plan_result, wait_for_plan


@pytest.fixture
def plan_db(tmp_path):
    path = tmp_path / "core.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE cognition_goal_proposals (
                proposal_id TEXT PRIMARY KEY, status TEXT, action_detail TEXT);
            CREATE TABLE bean_goal_runs (proposal_id TEXT, error TEXT);
            CREATE TABLE bean_orchestration_outputs (
                proposal_id TEXT PRIMARY KEY, output_json TEXT, output_sha256 TEXT);
        """)
    return path


def insert_step(db, index, total, status, output=None, digest=None, plan_id="test-plan"):
    pid = plan_proposal_id(plan_id, index)
    detail = {"capability": CAPABILITY, "tool": "numeric_context",
              "goal_plan": {"schema": PLAN_SCHEMA, "id": plan_id,
                            "step": index, "steps": total}}
    db.execute("INSERT INTO cognition_goal_proposals VALUES (?,?,?)",
               (pid, status, json.dumps(detail)))
    if output is not None:
        raw = json.dumps(output)
        db.execute("INSERT INTO bean_orchestration_outputs VALUES (?,?,?)",
                   (pid, raw, digest or hashlib.sha256(raw.encode()).hexdigest()))
    return pid


def test_completed_plan_returns_actual_outputs(plan_db):
    with sqlite3.connect(plan_db) as db:
        insert_step(db, 0, 2, "completed", {"value": 42})
        insert_step(db, 1, 2, "completed", {"answer": 84})
    result = wait_for_plan(plan_db, "test-plan", timeout=0.1)
    assert result["status"] == "completed"
    assert result["steps"][1]["output"] == {"answer": 84}


def test_failure_returns_latest_error_and_does_not_wait(plan_db):
    with sqlite3.connect(plan_db) as db:
        pid = insert_step(db, 0, 2, "failed")
        insert_step(db, 1, 2, "pending")
        db.executemany("INSERT INTO bean_goal_runs VALUES (?,?)",
                       [(pid, "old failure"), (pid, "current failure")])
    result = wait_for_plan(plan_db, "test-plan", timeout=0.1)
    assert result["status"] == "failed"
    assert result["steps"][0]["error"] == "current failure"


def test_missing_plan_timeout_is_not_completion_or_cancellation(plan_db):
    result = wait_for_plan(plan_db, "test-plan", timeout=0.01, interval=0.002)
    assert result["status"] == "pending"
    assert result["wait_timed_out"] is True
    assert result["cancelled"] is False


def test_running_plan_timeout_preserves_completed_steps(plan_db):
    with sqlite3.connect(plan_db) as db:
        insert_step(db, 0, 2, "completed", {"value": 42})
        insert_step(db, 1, 2, "running")
    result = wait_for_plan(plan_db, "test-plan", timeout=0.01, interval=0.002)
    assert result["status"] == "running"
    assert result["steps"][0]["output"] == {"value": 42}
    assert result["wait_timed_out"] is True


def test_tampered_output_cannot_be_reported_as_success(plan_db):
    with sqlite3.connect(plan_db) as db:
        insert_step(db, 0, 1, "completed", {"value": 42}, digest="invalid")
    with pytest.raises(ValueError, match="digest mismatch"):
        read_plan_result(plan_db, "test-plan")


def test_missing_step_and_missing_output_fail_closed(plan_db):
    with sqlite3.connect(plan_db) as db:
        insert_step(db, 0, 2, "pending")
    with pytest.raises(ValueError, match="missing persisted"):
        read_plan_result(plan_db, "test-plan")
    with sqlite3.connect(plan_db) as db:
        db.execute("DELETE FROM cognition_goal_proposals")
        insert_step(db, 0, 1, "completed")
    with pytest.raises(ValueError, match="lacks output"):
        read_plan_result(plan_db, "test-plan")


def test_rejected_inbox_returns_without_waiting(plan_db, tmp_path):
    inbox = tmp_path / "inbox"
    failed = inbox / "failed"
    failed.mkdir(parents=True)
    queued = inbox / "request.json"
    (failed / queued.name).write_text("{}")
    result = wait_for_plan(plan_db, "test-plan", timeout=0.1, queued_path=queued)
    assert result["status"] == "rejected"
    assert result["reason"] == "core_inbox_rejected"
    assert "wait_timed_out" not in result


def test_resume_after_timeout_reads_original_plan_without_resubmission(plan_db):
    with sqlite3.connect(plan_db) as db:
        pid = insert_step(db, 0, 1, "running")
    first = wait_for_plan(plan_db, "test-plan", timeout=0.01, interval=0.002)
    assert first["wait_timed_out"] is True
    with sqlite3.connect(plan_db) as db:
        raw = json.dumps({"answer": 12})
        db.execute("INSERT INTO bean_orchestration_outputs VALUES (?,?,?)",
                   (pid, raw, hashlib.sha256(raw.encode()).hexdigest()))
        db.execute("UPDATE cognition_goal_proposals SET status='completed' WHERE proposal_id=?", (pid,))
    result = wait_for_plan(plan_db, "test-plan", timeout=0.1)
    assert result["status"] == "completed"
    assert result["steps"][0]["output"] == {"answer": 12}


def _recovery_table(db):
    db.execute("CREATE TABLE bean_orchestration_recovery (parent_id TEXT PRIMARY KEY,"
               "child_id TEXT, depth INTEGER, state TEXT, error TEXT)")


def _link(db, parent, depth, state, error=None):
    child = "recovery:" + hashlib.sha256(parent.encode()).hexdigest()
    db.execute("INSERT INTO bean_orchestration_recovery VALUES (?,?,?,?,?)",
               (parent, child, depth, state, error))
    return child


def test_follow_completed_recovery_returns_real_child_outputs(plan_db):
    with sqlite3.connect(plan_db) as db:
        _recovery_table(db)
        insert_step(db, 0, 1, "failed")
        child = _link(db, "test-plan", 1, "submitted")
        insert_step(db, 0, 1, "completed", {"answer": 21}, plan_id=child)
    result = wait_for_plan(plan_db, "test-plan", timeout=0.1)
    assert result["status"] == "completed"
    assert result["plan_id"] == "test-plan"
    assert result["effective_plan_id"] == child
    assert result["initial_status"] == "failed"
    assert result["steps"][0]["output"] == {"answer": 21}
    assert result["recovery_lineage"][0]["parent_steps"][0]["status"] == "failed"
    assert read_plan_result(plan_db, "test-plan")["status"] == "failed"


def test_pending_recovery_times_out_without_cancelling(plan_db):
    with sqlite3.connect(plan_db) as db:
        _recovery_table(db)
        insert_step(db, 0, 1, "failed")
    r = wait_for_plan(plan_db, "test-plan", timeout=0.01, interval=0.002)
    assert r["status"] == "recovering" and r["wait_timed_out"]
    assert r["cancelled"] is False


def test_exhausted_recovery_reports_failure(plan_db):
    with sqlite3.connect(plan_db) as db:
        _recovery_table(db)
        insert_step(db, 0, 1, "failed")
        _link(db, "test-plan", 1, "planner_failed", "invalid plan")
    r = wait_for_plan(plan_db, "test-plan", timeout=0.1)
    assert r["status"] == "failed"
    assert r["recovery_lineage"][0]["error"] == "invalid plan"
    assert "wait_timed_out" not in r


def test_recovery_corruption_is_not_success(plan_db):
    with sqlite3.connect(plan_db) as db:
        _recovery_table(db)
        insert_step(db, 0, 1, "failed")
        child = _link(db, "test-plan", 1, "submitted")
        insert_step(db, 0, 1, "completed", {"answer": 21}, digest="bad", plan_id=child)
    with pytest.raises(ValueError, match="digest mismatch"):
        read_plan_result(plan_db, "test-plan", follow_recovery=True)


def test_recovery_depth_is_bounded(plan_db):
    with sqlite3.connect(plan_db) as db:
        _recovery_table(db)
        parent = "test-plan"
        insert_step(db, 0, 1, "failed")
        for depth in range(1, 4):
            child = _link(db, parent, depth, "submitted")
            insert_step(db, 0, 1, "failed", plan_id=child)
            parent = child
    r = wait_for_plan(plan_db, "test-plan", timeout=0.1)
    assert r["status"] == "failed"
    assert len(r["recovery_lineage"]) == 3
    assert r["effective_plan_id"] == parent
