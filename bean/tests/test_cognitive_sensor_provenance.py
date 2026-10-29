"""Provenance-aware pooling: known shared evidence is not independent."""
import hashlib
import json
import unittest
from experiments.cognitive_gauntlet.sensor_reliability import (
    OnlineSensorTrust, SensorObservation)
from experiments.cognitive_gauntlet.sensor_provenance import benchmark, REGIMES, ARMS


class ProvenancePoolingTests(unittest.TestCase):
    def test_three_shared_wrong_votes_do_not_outvote_two_independent(self):
        observations = [SensorObservation(str(i), f"s{i}", 0 if i < 3 else 1)
                        for i in range(5)]
        groups = {f"s{i}": "bus" if i < 3 else f"s{i}" for i in range(5)}
        raw = OnlineSensorTrust().forecast(observations)
        grouped = OnlineSensorTrust().forecast(
            observations, provenance_groups=groups)
        self.assertLess(raw, .5)
        self.assertGreater(grouped, .5)

    def test_unique_groups_reproduce_unchanged_baseline_and_learning(self):
        baseline, candidate = OnlineSensorTrust(decay=.97), OnlineSensorTrust(decay=.97)
        for step in range(12):
            observations = [SensorObservation(f"{step}:{i}", f"s{i}",
                                              (step + i) % 2) for i in range(5)]
            groups = {f"s{i}": f"s{i}" for i in range(5)}
            self.assertEqual(baseline.forecast(observations),
                             candidate.forecast(observations, provenance_groups=groups))
            baseline.learn(step % 2)
            candidate.learn(step % 2)
        self.assertEqual(baseline.state(), candidate.state())

    def test_bad_group_mapping_cannot_consume_receipt(self):
        model = OnlineSensorTrust()
        observations = [SensorObservation("a", "s0", 1),
                        SensorObservation("b", "s1", 0)]
        for bad in ({}, {"s0": "bus"}, {"s0": "bus", "s1": ""},
                    {"s0": "bus", "s1": " padded "},
                    {"s0": "bus", "s1": 7},
                    {"s0": "bus", "s1": "ok", "extra": "bus"}, []):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    model.forecast(observations, provenance_groups=bad)
        model.forecast(observations, provenance_groups={"s0": "bus", "s1": "bus"})
        model.skip_feedback(reason="unavailable")
        self.assertEqual(len(model.receipts), 1)

    def test_missing_feedback_and_restore_keep_original_counts(self):
        model = OnlineSensorTrust(decay=.97)
        model.forecast([SensorObservation("a", "s0", 1)],
                       provenance_groups={"s0": "bus"})
        model.learn(1)
        before = dict(model.counts)
        model.forecast([SensorObservation("b", "s0", 0)],
                       provenance_groups={"s0": "bus"})
        model.skip_feedback(reason="host_outcome_unavailable")
        self.assertEqual(model.counts, before)
        restored = OnlineSensorTrust.restore(json.loads(json.dumps(model.state())))
        self.assertEqual(model.state(), restored.state())
        with self.assertRaises(ValueError):
            restored.forecast([SensorObservation("b", "s0", 1)])

    def test_incorrect_grouping_can_regress(self):
        observations = [SensorObservation(str(i), f"s{i}", 1 if i < 3 else 0)
                        for i in range(5)]
        groups = {f"s{i}": "wrong_bus" if i < 3 else f"s{i}" for i in range(5)}
        raw = OnlineSensorTrust().forecast(observations)
        grouped = OnlineSensorTrust().forecast(
            observations, provenance_groups=groups)
        self.assertGreater((grouped - 1) ** 2, (raw - 1) ** 2)

    def test_case_level_heldout_reconciliation(self):
        report = benchmark(seeds=2, rounds=20)
        self.assertEqual(report, benchmark(seeds=2, rounds=20))
        self.assertEqual(len(report["cases"]), len(REGIMES) * 2 * 20)
        self.assertEqual(report["external_runtimes_executed"], [])
        unsigned = {key: value for key, value in report.items() if key != "digest"}
        raw = json.dumps(unsigned, sort_keys=True, separators=(",", ":"),
                         allow_nan=False)
        self.assertEqual(report["digest"], hashlib.sha256(raw.encode()).hexdigest())
        for regime, score in report["scores"].items():
            rows = [row for row in report["cases"]
                    if regime == "all" or row["regime"] == regime]
            self.assertEqual(score["n"], len(rows))
            self.assertEqual(score["missing"],
                             sum(not row["feedback_available"] for row in rows))
            for arm in ARMS:
                self.assertAlmostEqual(score["mse"][arm],
                    sum(row["losses"][arm] for row in rows) / len(rows))
            for row in rows:
                if not row["feedback_available"]:
                    self.assertEqual(row["trust_counts_before_feedback"],
                                     row["trust_counts_after_feedback"])
                if row["regime"] == "independent":
                    self.assertEqual(row["predictions"]["ungrouped"],
                                     row["predictions"]["provenance_grouped"])


if __name__ == "__main__":
    unittest.main()
