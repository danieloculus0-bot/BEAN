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


def insert_step(db, index, total, status, output=None, digest=None):
    pid = plan_proposal_id("test-plan", index)
    detail = {"capability": CAPABILITY, "tool": "numeric_context",
              "goal_plan": {"schema": PLAN_SCHEMA, "id": "test-plan",
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
