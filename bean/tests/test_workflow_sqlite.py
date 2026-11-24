"""Exercise real workflow SQLite evidence, with native planner boundary doubles."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from bean.runtime.verified_workflows import VerifiedWorkflows, CAPABILITY


class Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE IF NOT EXISTS cognition_goal_proposals "
                          "(proposal_id TEXT PRIMARY KEY, action_detail TEXT)")
        self.conn.commit()

    def _conn(self):
        return self.conn

    def fetchone(self, sql, params):
        return self.conn.execute(sql, params).fetchone()

    def execute(self, sql, params):
        return self.conn.execute(sql, params)

    def commit(self):
        self.conn.commit()


class WorkflowSQLiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "memory.sqlite"
        self.open_memory()

    def open_memory(self):
        self.store = Store(self.path)
        self.owner = Mock()
        self.owner.store = self.store
        self.owner.tools = {"retained_weighted_mean": None}
        self.memory = VerifiedWorkflows(self.owner)

    def tearDown(self):
        self.store.conn.close()
        self.tmp.cleanup()

    def observe(self, pid, values, weights, correct=True):
        inputs = {"values": values, "weights": weights}
        # Host evaluator calculates the expected result independently.
        expected = sum(v*w for v,w in zip(values, weights)) / sum(weights)
        actual = expected if correct else expected + 1
        detail = {"capability": CAPABILITY, "tool": "retained_weighted_mean",
                  "args": inputs, "inputs": inputs}
        self.store.execute("INSERT INTO cognition_goal_proposals VALUES (?,?)",
                           (pid, json.dumps(detail)))
        self.store.commit()
        self.owner.status.return_value = {"status": "completed", "steps": [
            {"proposal_id": pid, "output": {"value": actual}}]}
        return self.memory.feedback(family="weighted", plan_id=pid,
            checks=[{"step": 0, "path": ["value"], "expected": expected}],
            evidence_ref="independent-synthetic-oracle")

    def test_retention_across_database_reopen_and_fresh_input(self):
        first = self.observe("a", [3, 7], [1, 2])
        self.assertTrue(first["passed"])
        self.assertEqual(self.memory.candidates("weighted"), [])
        second = self.observe("b", [8, 2, 1], [2, 3, 4])
        self.assertEqual(first["graph_sha"], second["graph_sha"])
        self.store.conn.close()
        self.open_memory()
        candidates = self.memory.candidates("weighted")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["distinct_verified_inputs"], 2)
        fresh = {"values": [19, 27, 3], "weights": [1, 3, 2]}
        result = self.memory.plan_with_memory(family="weighted", objective="Estimate",
                                               inputs=fresh, plan_id="new")
        self.assertEqual(result["route"], "retained")
        self.owner.submit.assert_not_called()
        step = self.owner.engine.propose_plan.call_args.args[2][0]
        self.assertEqual(step.action_detail["inputs"], fresh)
        self.assertEqual(step.action_detail["args"], {
            "values": {"$input": ["values"]}, "weights": {"$input": ["weights"]}})

    def test_duplicate_input_and_negative_feedback_do_not_promote(self):
        self.observe("a", [3, 7], [1, 2])
        self.observe("b", [3, 7], [1, 2])
        self.assertEqual(self.memory.candidates("weighted"), [])
        self.observe("c", [5, 6], [2, 1])
        self.assertEqual(len(self.memory.candidates("weighted")), 1)
        failed = self.observe("d", [9, 1], [3, 2], correct=False)
        self.assertFalse(failed["passed"])
        self.assertEqual(self.memory.candidates("weighted"), [])
        result = self.memory.plan_with_memory(family="weighted", objective="Estimate",
            inputs={"values": [1, 2], "weights": [2, 1]}, plan_id="new")
        self.assertEqual(result["route"], "fresh_fallback")
        self.owner.engine.propose_plan.assert_not_called()
        self.owner.submit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
