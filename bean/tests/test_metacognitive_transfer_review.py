"""Synthetic, paired method-reconsideration cases; not proof of consciousness."""
import copy
import unittest
from bean.learning.transfer_gate import evaluate_transfer, reconsider_transfer


class ReconsiderationTests(unittest.TestCase):
    def setUp(self):
        self.earlier = evaluate_transfer(
            retained="old_method", alternative="new_method",
            probe_ids=("early1", "early2"),
            reward=lambda m, _: 2 if m == "old_method" else 1)

    def test_changed_objective_reverses_method_and_preserves_history(self):
        original = copy.deepcopy(self.earlier)
        report = reconsider_transfer(
            prior=self.earlier, probe_ids=("later1", "later2"),
            reward=lambda m, _: 0 if m == "old_method" else 3)
        self.assertEqual(report["previous_method"], "old_method")
        self.assertEqual(report["reconsidered_method"], "new_method")
        self.assertEqual(report["outcome"], "revised")
        self.assertTrue(report["decision_changed"])
        self.assertEqual(report["initial_receipt"], original)
        self.assertEqual(self.earlier, original)
        self.assertEqual(len(report["fresh_review"]["pairs"]), 2)
        self.earlier["pairs"][0]["retained_reward"] = -99
        self.assertEqual(report["initial_receipt"], original)

    def test_still_good_method_is_retained(self):
        report = reconsider_transfer(
            prior=self.earlier, probe_ids=["fresh1"],
            reward=lambda m, _: 3 if m == "old_method" else 0)
        self.assertEqual(report["reconsidered_method"], "old_method")
        self.assertEqual(report["outcome"], "confirmed")
        self.assertFalse(report["decision_changed"])

    def test_inconclusive_new_evidence_abstains_instead_of_overclaiming(self):
        report = reconsider_transfer(
            prior=self.earlier, probe_ids=["fresh1"],
            reward=lambda *_: 1)
        self.assertIsNone(report["reconsidered_method"])
        self.assertEqual(report["outcome"], "uncertain_now")

    def test_replayed_and_duplicate_probes_fail_before_reward_is_called(self):
        called = []
        for probes in (["early1"], ["fresh1", "fresh1"], []):
            with self.subTest(probes=probes), self.assertRaises(ValueError):
                reconsider_transfer(prior=self.earlier, probe_ids=probes,
                                    reward=lambda *args: called.append(args))
        self.assertEqual(called, [])

    def test_tampered_prior_and_nonfinite_new_rewards_are_rejected(self):
        altered = copy.deepcopy(self.earlier)
        altered["pairs"][0]["retained_reward"] = 900
        with self.assertRaisesRegex(ValueError, "changed"):
            reconsider_transfer(prior=altered, probe_ids=["fresh1"],
                                reward=lambda *_: 1)
        with self.assertRaisesRegex(ValueError, "Finite observed"):
            reconsider_transfer(prior=self.earlier, probe_ids=["fresh1"],
                                reward=lambda *_: float("nan"))


if __name__ == "__main__":
    unittest.main()
