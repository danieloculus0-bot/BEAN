"""Regression for persistent recovery of a transient planner failure."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from bean.cognition.goal_state import PLAN_SCHEMA, plan_proposal_id
from bean.runtime.native_orchestration import CAPABILITY
from bean.runtime.orchestration_recovery import DurableRecovery, SCHEMA


class Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    def _conn(self):
        return self.conn

    def execute(self, sql, args=()):
        return self.conn.execute(sql, args)

    def fetchone(self, sql, args=()):
        return self.execute(sql, args).fetchone()

    def fetchall(self, sql, args=()):
        return self.execute(sql, args).fetchall()

    def commit(self):
        self.conn.commit()


class RecoveryRetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "recovery.sqlite"
        self.store = Store(self.path)
        self.addCleanup(lambda: self.store.conn.close())
        self.store.conn.executescript("""
          CREATE TABLE cognition_goal_proposals
            (proposal_id TEXT, action_detail TEXT, status TEXT);
          CREATE TABLE bean_goal_runs
            (proposal_id TEXT, error TEXT, result_json TEXT, started_at TEXT);
        """)
        self.pid = plan_proposal_id("parent", 0)
        detail = {"capability": CAPABILITY, "objective": "recover", "inputs": {},
                  "goal_plan": {"schema": PLAN_SCHEMA, "id": "parent", "step": 0, "steps": 1}}
        self.store.execute("INSERT INTO cognition_goal_proposals VALUES (?,?,?)",
                           (self.pid, json.dumps(detail), "failed"))
        self.store.commit()

    def owner(self, side_effect):
        def status(plan_id):
            if plan_id == "parent":
                return {"status": "failed", "steps": [
                    {"status": "failed", "step": 0, "proposal_id": self.pid, "tool": "reason"}]}
            return {"status": "pending", "steps": []}
        return SimpleNamespace(store=self.store, cycle=SimpleNamespace(poll_due=Mock(return_value=[])),
                               status=Mock(side_effect=status), submit=Mock(side_effect=side_effect))

    def row(self):
        return dict(self.store.fetchone("SELECT * FROM bean_orchestration_recovery"))

    def test_failure_then_restart_and_resubmit_same_child(self):
        recovery = DurableRecovery(self.owner(RuntimeError("temporary provider failure")))
        recovery.advance()
        row = self.row()
        self.assertEqual((row["state"], row["attempts"]), ("pending", 1))
        self.assertIsNone(recovery.status("parent")["recovery_lineage"][0]["plan"])
        self.store.conn.close()
        self.store = Store(self.path)
        owner = self.owner(None)
        recovery = DurableRecovery(owner)
        recovery.advance()
        owner.submit.assert_called_once()
        self.assertEqual(owner.submit.call_args.kwargs["plan_id"], row["child_id"])
        self.assertEqual((self.row()["state"], self.row()["attempts"]), ("submitted", 2))
        self.assertEqual(recovery.status("parent")["effective_status"], "pending")
        recovery.advance()
        owner.submit.assert_called_once()

    def test_permanent_failure_is_bounded(self):
        owner = self.owner(RuntimeError("still unavailable"))
        recovery = DurableRecovery(owner)
        for _ in range(6):
            recovery.advance()
        self.assertEqual(owner.submit.call_count, 3)
        self.assertEqual((self.row()["state"], self.row()["attempts"]), ("planner_failed", 3))

    def test_old_failed_row_is_recovered(self):
        self.store.conn.executescript(SCHEMA)
        evidence = {"parent": "parent", "completed": {}, "failures": []}
        self.store.execute("INSERT INTO bean_orchestration_recovery VALUES (?,?,?,?,?,?)",
                           ("parent", "old-child", 1, json.dumps(evidence), "planner_failed", "old"))
        self.store.commit()
        owner = self.owner(None)
        DurableRecovery(owner).advance()
        self.assertEqual((self.row()["state"], self.row()["attempts"]), ("submitted", 2))


if __name__ == "__main__":
    unittest.main()
