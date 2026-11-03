"""Synthetic accounting controls, not BEAN learning measurements."""
import unittest
from research.transfer_eval.budget_parity import audit_budget_parity

def trial(case, baseline=(10, 2, 3), candidate=(10, 2, 3)):
    keys = ("inference_tokens", "tool_calls", "training_updates")
    return {"case_id": case, "baseline": dict(zip(keys, baseline)),
            "candidate": dict(zip(keys, candidate))}

class BudgetParityTests(unittest.TestCase):
    def test_equal_budgets(self):
        result = audit_budget_parity([trial("a"), trial("b")])
        self.assertTrue(result["candidate_not_advantaged"])
        self.assertEqual(result["totals"]["candidate"]["tool_calls"], 4)

    def test_extra_inference(self):
        result = audit_budget_parity([trial("a", candidate=(11, 2, 3))])
        self.assertFalse(result["candidate_not_advantaged"])
        self.assertEqual(result["violations"][0]["resource"], "inference_tokens")

    def test_equal_aggregate_hides_per_case_advantage(self):
        result = audit_budget_parity([trial("a", candidate=(11, 2, 3)),
                                      trial("b", candidate=(9, 2, 3))])
        self.assertEqual(result["totals"]["baseline"], result["totals"]["candidate"])
        self.assertFalse(result["candidate_not_advantaged"])

    def test_tool_and_training_advantage(self):
        result = audit_budget_parity([trial("a", candidate=(10, 3, 4))])
        self.assertEqual({v["resource"] for v in result["violations"]},
                         {"tool_calls", "training_updates"})

    def test_invalid_metadata_fails_closed(self):
        bad = trial("a")
        bad["candidate"]["tool_calls"] = True
        with self.assertRaises(ValueError):
            audit_budget_parity([bad])
        with self.assertRaises(ValueError):
            audit_budget_parity([trial("a"), trial("a")])
        with self.assertRaises(ValueError):
            audit_budget_parity([trial("a", candidate=(-1, 2, 3))])
        with self.assertRaises(ValueError):
            audit_budget_parity([])

if __name__ == "__main__":
    unittest.main()
