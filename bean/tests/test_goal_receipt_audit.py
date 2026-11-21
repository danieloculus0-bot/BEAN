"""Read-only GoalCycle receipt audit contract tests."""
import hashlib
import json
import unittest

from bean.runtime.goal_cycle import GoalCycle


class _Store:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self, sql, params):
        assert "bean_goal_runs" in sql
        return self.rows[:params[0]]


class ReceiptAuditTests(unittest.TestCase):
    def test_audit_does_not_execute_or_reclassify_outcomes(self):
        raw = json.dumps({"observed": 4}, sort_keys=True)
        cycle = object.__new__(GoalCycle)
        cycle.store = _Store([
            {"run_id": "r1", "proposal_id": "p1", "state": "success",
             "decision_json": "{}", "result_json": raw},
            {"run_id": "r2", "proposal_id": "p2", "state": "unknown",
             "decision_json": "{}", "result_json": None},
            {"run_id": "r3", "proposal_id": "p3", "state": "failed",
             "decision_json": "{}", "result_json": "{bad"},
        ])
        rows = cycle.audit_receipts()
        self.assertEqual(rows[0]["result_sha256"],
                         hashlib.sha256(raw.encode()).hexdigest())
        self.assertFalse(rows[0]["independent_outcome_verified"])
        self.assertIsNone(rows[1]["result_sha256"])
        self.assertEqual(rows[1]["state"], "unknown")
        self.assertFalse(rows[2]["result_json_valid"])

    def test_truncation_is_explicit(self):
        cycle = object.__new__(GoalCycle)
        cycle.store = _Store([{
            "run_id": "r", "proposal_id": "p", "state": "success",
            "decision_json": "{}",
            "result_json": json.dumps({"schema": "bean.goal.result_truncated.v1",
                                       "truncated": True}),
        }])
        self.assertTrue(cycle.audit_receipts()[0]["result_truncated"])
        with self.assertRaises(ValueError):
            cycle.audit_receipts(limit=0)


if __name__ == "__main__":
    unittest.main()
