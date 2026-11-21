"""Independent feedback persistence contract for GoalCycle (synthetic SQLite rows)."""
import hashlib
import json
import sqlite3
from unittest.mock import Mock
import pytest
from bean.runtime.goal_cycle import GoalCycle


def test_external_feedback_immutable_and_does_not_replay(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "goal.db"))
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE bean_goal_runs (
        run_id TEXT PRIMARY KEY, proposal_id TEXT, action_type TEXT,
        state TEXT, result_json TEXT)""")
    conn.execute("INSERT INTO bean_goal_runs VALUES (?,?,?,?,?)",
                 ("r1", "p1", "inspect", "success", '{"value":7}'))
    conn.commit()
    cycle = object.__new__(GoalCycle)
    cycle.store = Mock()
    cycle.store._conn.return_value = conn
    cycle.store.fetchone.side_effect = lambda sql, params: conn.execute(sql, params).fetchone()
    action = Mock()
    cycle.actions = {"inspect": action}
    receipt = cycle.evaluate_run("r1", lambda evidence: {
        "correct": evidence["result"]["value"] == 7,
        "evaluator": "synthetic-external", "reason": "matched expected value"})
    assert receipt["correct"] is True
    assert receipt["execution_state_unchanged"] is True
    assert action.call_count == 0
    stored = conn.execute("SELECT verdict_json,verdict_sha256 FROM bean_goal_feedback").fetchone()
    assert hashlib.sha256(stored["verdict_json"].encode()).hexdigest() == stored["verdict_sha256"]
    with pytest.raises(sqlite3.IntegrityError):
        cycle.evaluate_run("r1", lambda _: {"correct": False})
    assert conn.execute("SELECT state FROM bean_goal_runs").fetchone()[0] == "success"


def test_feedback_rejects_unfinished_or_unscored(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "goal.db"))
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE bean_goal_runs (run_id TEXT,proposal_id TEXT,action_type TEXT,state TEXT,result_json TEXT)")
    conn.execute("INSERT INTO bean_goal_runs VALUES ('r','p','inspect','running',NULL)")
    conn.commit()
    cycle = object.__new__(GoalCycle)
    cycle.store = Mock()
    cycle.store._conn.return_value = conn
    cycle.store.fetchone.side_effect = lambda sql, params: conn.execute(sql, params).fetchone()
    with pytest.raises(ValueError):
        cycle.evaluate_run("r", lambda _: {"correct": True})
    conn.execute("UPDATE bean_goal_runs SET state='success'")
    conn.commit()
    with pytest.raises(ValueError):
        cycle.evaluate_run("r", lambda _: {"score": 1})
