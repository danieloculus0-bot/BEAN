"""Executable held-out audit acceptance for native transfer."""
import unittest
from bean.learning.transfer_gate import evaluate_transfer
from bean.learning.transfer_holdout import audit_transfer


class TransferHoldoutTests(unittest.TestCase):
    def setUp(self):
        self.selection = evaluate_transfer(
            retained="retained", alternative="alternative",
            probe_ids=["probe-1", "probe-2"],
            reward=lambda policy, task: 2 if policy == "retained" else 1)
        self.controls = dict(frozen="frozen", no_memory="cold",
                             grammar_matched="grammar", strong="strong")

    def test_paired_holdout_advantage(self):
        calls = []
        def reward(policy, task):
            calls.append((policy, task))
            return 2 if policy == "retained" else 1
        result = audit_transfer(selection=self.selection,
                                holdout_ids=["novel-A", "novel-B"],
                                controls=self.controls, reward=reward)
        self.assertTrue(result["passed"])
        self.assertEqual(result["task_count"], 2)
        self.assertEqual(len(calls), 10)
        self.assertEqual(set(result["advantages"].values()), {1.0})

    def test_reject_overlap_and_tamper(self):
        with self.assertRaises(ValueError):
            audit_transfer(selection=self.selection,
                           holdout_ids=["probe-1", "novel-B"],
                           controls=self.controls, reward=lambda *_: 1)
        modified = dict(self.selection, selected="alternative")
        with self.assertRaises(ValueError):
            audit_transfer(selection=modified, holdout_ids=["a", "b"],
                           controls=self.controls, reward=lambda *_: 1)

    def test_strong_control_prevents_promotion(self):
        result = audit_transfer(selection=self.selection,
                                holdout_ids=["a", "b"], controls=self.controls,
                                reward=lambda p, _: 3 if p == "strong" else 2)
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
