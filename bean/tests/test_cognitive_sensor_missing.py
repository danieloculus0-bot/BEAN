"""Unobserved feedback must never become a false learning reward."""
import copy
import hashlib
import json
import unittest
from experiments.cognitive_gauntlet.sensor_reliability import OnlineSensorTrust, SensorObservation
from experiments.cognitive_gauntlet.sensor_missing_feedback import benchmark, REGIMES, ARMS


class MissingFeedbackTests(unittest.TestCase):
    def test_missing_feedback_does_not_learn_or_decay(self):
        model = OnlineSensorTrust(decay=.5)
        model.forecast([SensorObservation("observed", "s0", 1)])
        model.learn(1)
        before = copy.deepcopy(model.counts)
        model.forecast([SensorObservation("missing", "s0", 0)])
        model.skip_feedback(reason="host_outcome_unavailable")
        self.assertEqual(model.counts, before)
        self.assertIsNone(model.receipts[-1]["outcome"])
        self.assertEqual(model.receipts[-1]["feedback_status"], "missing")
        with self.assertRaises(ValueError):
            model.learn(0)
        with self.assertRaises(ValueError):
            model.forecast([SensorObservation("missing", "s0", 1)])
        model.forecast([SensorObservation("fresh", "s0", 1)])
        model.learn(1)

    def test_invalid_skip_cannot_silently_close_pending(self):
        model = OnlineSensorTrust()
        with self.assertRaises(ValueError):
            model.skip_feedback(reason="missing")
        model.forecast([SensorObservation("a", "s0", 1)])
        for bad in ("", " ", " padded ", "x" * 121, None, 7):
            with self.assertRaises(ValueError):
                model.skip_feedback(reason=bad)
        with self.assertRaises(ValueError):
            model.forecast([SensorObservation("b", "s0", 1)])
        model.skip_feedback(reason="unavailable")
        with self.assertRaises(ValueError):
            model.skip_feedback(reason="unavailable")

    def test_restart_preserves_missing_receipts_and_blocks_reuse(self):
        model = OnlineSensorTrust(decay=.97)
        model.forecast([SensorObservation("e0", "s0", 0)])
        model.skip_feedback(reason="unavailable")
        restored = OnlineSensorTrust.restore(json.loads(json.dumps(model.state())))
        self.assertEqual(restored.state(), model.state())
        with self.assertRaises(ValueError):
            restored.forecast([SensorObservation("e0", "s0", 1)])
        restored.forecast([SensorObservation("e1", "s0", 1)])
        restored.learn(1)
        self.assertEqual(restored.receipts[0]["feedback_status"], "missing")
        self.assertEqual(restored.receipts[1]["outcome"], 1)

    def test_corrupt_missing_receipt_rejected(self):
        model = OnlineSensorTrust()
        model.forecast([SensorObservation("e0", "s0", 0)])
        model.skip_feedback(reason="unavailable")
        for field, bad in (("outcome", 0), ("reason", ""),
                           ("feedback_status", "fabricated")):
            state = copy.deepcopy(model.state())
            state["receipts"][0][field] = bad
            with self.assertRaises(ValueError):
                OnlineSensorTrust.restore(state)

    def test_independent_heldout_replays_all_skips_and_losses(self):
        report = benchmark(seeds=2, rounds=20)
        self.assertEqual(report, benchmark(seeds=2, rounds=20))
        self.assertEqual(len(report["cases"]), len(REGIMES) * 2 * 20)
        self.assertEqual(report["external_runtimes_executed"], [])
        unsigned = {k: v for k, v in report.items() if k != "digest"}
        payload = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False)
        self.assertEqual(report["digest"], hashlib.sha256(payload.encode()).hexdigest())
        for regime, score in report["scores"].items():
            cases = [x for x in report["cases"]
                     if regime == "all" or x["regime"] == regime]
            self.assertEqual(score["missing"], sum(not x["feedback_available"] for x in cases))
            for arm in ARMS:
                self.assertAlmostEqual(score["mse"][arm],
                    sum(x["losses"][arm] for x in cases) / len(cases))
            for row in cases:
                if not row["feedback_available"]:
                    self.assertEqual(row["trust_counts_before_feedback"],
                                     row["trust_counts_after_feedback"])

    def test_checkpoint_rejects_inconsistent_evidence_identity(self):
        model = OnlineSensorTrust()
        model.forecast([SensorObservation("a", "s0", 1)])
        model.learn(1)
        model.forecast([SensorObservation("b", "s0", 0)])
        model.skip_feedback(reason="unavailable")
        original = model.state()
        corrupted = []
        variant = copy.deepcopy(original)
        variant["seen_ids"].append("fabricated")
        corrupted.append(variant)
        variant = copy.deepcopy(original)
        variant["seen_ids"].pop()
        corrupted.append(variant)
        variant = copy.deepcopy(original)
        variant["seen_ids"][0] = 1
        corrupted.append(variant)
        variant = copy.deepcopy(original)
        variant["receipts"][0]["evidence_ids"] = ["a", "a"]
        corrupted.append(variant)
        variant = copy.deepcopy(original)
        variant["receipts"][1]["evidence_ids"] = ["a"]
        corrupted.append(variant)
        variant = copy.deepcopy(original)
        variant["receipts"][0]["evidence_ids"] = []
        corrupted.append(variant)
        variant = copy.deepcopy(original)
        variant["receipts"] = {"not": "a list"}
        corrupted.append(variant)
        for state in corrupted:
            with self.subTest(state=state):
                with self.assertRaises(ValueError):
                    OnlineSensorTrust.restore(state)
        self.assertEqual(OnlineSensorTrust.restore(original).state(), original)

    def test_checkpoint_and_restored_receipts_do_not_alias(self):
        model = OnlineSensorTrust()
        model.forecast([SensorObservation("original", "s0", 1)])
        model.learn(1)
        snapshot = model.state()
        snapshot["receipts"][0]["evidence_ids"][0] = "altered"
        self.assertEqual(model.state()["receipts"][0]["evidence_ids"], ["original"])
        original = model.state()
        restored = OnlineSensorTrust.restore(original)
        original["receipts"][0]["evidence_ids"][0] = "mutated_after_restore"
        self.assertEqual(restored.state()["receipts"][0]["evidence_ids"], ["original"])
        self.assertEqual(model.state(), restored.state())

    def test_forecast_rejects_nonstring_identity_before_consuming(self):
        model = OnlineSensorTrust()
        for observation in (SensorObservation(7, "s0", 1),
                            SensorObservation("valid", 7, 1),
                            SensorObservation("", "s0", 1)):
            with self.assertRaises(ValueError):
                model.forecast([observation])
        model.forecast([SensorObservation("valid", "s0", 1)])
        model.learn(1)
        self.assertEqual(model.state()["seen_ids"], ["valid"])


if __name__ == "__main__":
    unittest.main()
