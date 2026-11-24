"""Exercise real retained-workflow SQLite promotion and native preflight.

Synthetic observations test the routing and persistence contract, not AGI.
"""
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from bean.runtime.verified_workflows import (
    VerifiedWorkflows, canonical, digest, referenced_input_digest,
    register_verified_workflows,
)


class Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

    def _conn(self):
        return self.conn

    def commit(self):
        self.conn.commit()


class CandidateValidationTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.owner = SimpleNamespace(
            store=self.store, tools={"mean_sign": ("", Mock())},
            _validate_refs=Mock(), engine=Mock(), session_uuid="synthetic")
        self.memory = VerifiedWorkflows(self.owner)
        self.graph = [{"tool": "mean_sign",
                       "args": {"history": {"$input": ["history"]}}}]
        self.sha = digest(self.graph)
        self.seed("initial", {"history": [1, 2]})

    def tearDown(self):
        self.store.conn.close()

    def seed(self, pid, inputs, passed=1):
        self.store.conn.execute(
            "INSERT INTO bean_verified_workflow_trials VALUES (?,?,?,?,?,?,?)",
            ("test", pid, self.sha, canonical(self.graph),
             referenced_input_digest(self.graph, inputs),
             canonical({"parameterization_version": 2}), passed))
        self.store.commit()

    def test_single_observation_allows_validation_not_production(self):
        args = dict(family="test", inputs={"history": [-2, -3]},
                    plan_id="second", graph_sha=self.sha)
        self.assertEqual(self.memory.reuse(**args)["status"], "abstain")
        self.owner.engine.propose_plan.assert_not_called()
        result = self.memory.reuse(**args, validation=True)
        self.assertEqual(result["status"], "submitted")
        self.assertFalse(result["model_invoked"])
        self.owner.engine.propose_plan.assert_called_once()

    def test_only_distinct_referenced_inputs_count(self):
        self.seed("duplicate", {"history": [1, 2], "irrelevant": "new"})
        self.assertEqual(self.memory.candidates("test"), [])
        self.seed("distinct", {"history": [-2, -3]})
        self.assertEqual(self.memory.candidates("test")[0]["distinct_verified_inputs"], 2)
        self.assertEqual(self.memory.reuse(family="test", inputs={"history": [8, 9]},
                                          plan_id="third")["status"], "submitted")

    def test_negative_evidence_disqualifies_graph(self):
        self.seed("counterexample", {"history": [-2, -3]}, passed=0)
        self.assertEqual(self.memory.candidates("test", minimum=1), [])
        self.assertEqual(self.memory.reuse(family="test", inputs={"history": [8]},
                                          plan_id="third", validation=True)["status"], "abstain")

    def test_preflight_rejects_incompatible_new_inputs_before_queue(self):
        for bad in ("not numeric history", [], [1, True], [1, "2"]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.memory.reuse(family="test", inputs={"history": bad},
                                  plan_id="bad", graph_sha=self.sha, validation=True)
        self.owner.engine.propose_plan.assert_not_called()

    def test_production_inbox_cannot_override_threshold(self):
        handlers = {}
        inbox = SimpleNamespace(register=lambda name, fn: handlers.update({name: fn}))
        register_verified_workflows(inbox, self.owner)
        msg = SimpleNamespace(args=dict(family="test", inputs={"history": [8]},
                                        plan_id="second", graph_sha=self.sha, validation=True))
        self.assertEqual(handlers["cognition_workflow_reuse"](msg, None)["status"], "abstain")
        self.owner.engine.propose_plan.assert_not_called()
        self.assertEqual(handlers["cognition_workflow_validate"](msg, None)["status"], "submitted")


if __name__ == "__main__":
    unittest.main()
