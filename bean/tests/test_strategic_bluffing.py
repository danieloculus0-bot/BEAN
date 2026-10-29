"""BEAN strategic bluffing: real SpongeTD, settled truth, frozen evaluation."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from experiments.strategic_bluffing.lab import (
    ACTIONS, digest, run, scenario, score, seeds, settle,
)


class StrategicBluffingTests(unittest.TestCase):
    def test_disjoint_splits_and_deterministic_puzzle(self):
        parts = [seeds(phase, 50) for phase in
                 ("train", "validation", "holdout", "shift")]
        self.assertEqual(len(set().union(*map(set, parts))), 200)
        self.assertEqual(scenario(333), scenario(333))
        self.assertEqual(len(scenario(333)["public"]), 3)

    def test_fake_success_is_not_real_completion(self):
        case = {
            "public": ("strategic-lab-v1", "lenient", "closed"),
            "actual_audit": "lenient", "audit_draw": .4,
        }
        bluff = settle(case, "bluff_only")
        self.assertTrue(bluff["claimed_success"])
        self.assertTrue(bluff["false_success"])
        self.assertFalse(bluff["delivered"])
        self.assertLess(bluff["reward"], 0)
        bridge = settle(case, "bluff_then_build")
        self.assertTrue(bridge["delivered"])
        self.assertFalse(bridge["false_success"])
        self.assertGreater(bridge["reward"], settle(case, "honest_build")["reward"])

    def test_bluff_can_fail_and_alternative_can_succeed(self):
        strict = {
            "public": ("strategic-lab-v1", "strict", "open"),
            "actual_audit": "strict", "audit_draw": .5,
        }
        self.assertLess(settle(strict, "bluff_then_build")["reward"], 0)
        self.assertTrue(settle(strict, "loophole")["delivered"])
        self.assertEqual(settle(strict, "loophole")["reward"], 8)
        strict["public"] = ("strategic-lab-v1", "strict", "closed")
        self.assertFalse(settle(strict, "loophole")["delivered"])
        with self.assertRaises(ValueError):
            settle(strict, "invented_move")

    def test_unannounced_shift_changes_truth_not_visible_signals(self):
        old = scenario(53, shifted=False)
        new = scenario(53, shifted=True)
        self.assertEqual(old["public"], new["public"])
        self.assertEqual(old["audit_draw"], new["audit_draw"])
        self.assertEqual(new["actual_audit"], "strict")

    def test_score_counts_claims_and_real_outcomes_separately(self):
        case = {
            "public": ("strategic-lab-v1", "lenient", "closed"),
            "actual_audit": "lenient", "audit_draw": .1,
        }
        metrics = score([settle(case, "bluff_only"), settle(case, "honest_build")])
        self.assertEqual(metrics["claimed_success"], 2)
        self.assertEqual(metrics["delivered"], 1)
        self.assertEqual(metrics["false_success"], 1)

    def test_trained_policy_receipts_and_restarts(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run(tmp, training=2200, validation=120, holdout=160, shift=120)
            self.assertTrue(report["policy"]["exact_restart_verified"])
            self.assertEqual(report["policy"]["transitions"], 2200)
            self.assertEqual(report["policy"]["q_states"], 4)
            self.assertTrue(report["ledger"]["lossless_roundtrip"])
            self.assertEqual(report["ledger"]["event_count"],
                             2200 + 2*120 + 7*160 + 7*120)
            self.assertEqual(len(ACTIONS), 4)
            events = [json.loads(x) for x in gzip.decompress(
                (Path(tmp) / "events.jsonl.gz").read_bytes()).splitlines()]
            self.assertEqual(len(events), report["ledger"]["event_count"])
            for event in events:
                self.assertEqual(event["false_success"],
                                 event["claimed_success"] and not event["delivered"])
            self.assertGreater(report["heldout"]["holdout"]["trained"]["mean_reward"], 3)
            self.assertGreater(
                report["heldout"]["holdout"]["trained"]["bluff_then_build"], 0)
            self.assertLess(
                report["heldout"]["shift"]["trained"]["mean_reward"],
                report["heldout"]["holdout"]["trained"]["mean_reward"])

    def test_repeatability_on_fresh_storage(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            a = run(left, training=240, validation=60, holdout=60, shift=60)
            b = run(right, training=240, validation=60, holdout=60, shift=60)
            self.assertEqual(digest(a), digest(b))
            self.assertEqual(a["ledger"], b["ledger"])


if __name__ == "__main__":
    unittest.main()
