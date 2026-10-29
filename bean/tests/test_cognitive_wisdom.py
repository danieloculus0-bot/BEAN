"""Evidence-backed checks for the five-dimension cognitive measurement."""
import hashlib
import json
import unittest

from experiments.cognitive_gauntlet.schrodinger_benchmark import benchmark, ARMS
from experiments.cognitive_gauntlet.wisdom_measurement import measure, WISDOM_SCHEMA


class WisdomMeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = benchmark(first_seed=8000, seeds=2, rounds=20)
        cls.measured = measure(cls.source)

    def test_all_cases_reconciled(self):
        r = self.measured
        self.assertEqual(r["schema"], WISDOM_SCHEMA)
        self.assertEqual(r["cases_included"], len(self.source["cases"]))
        self.assertEqual(r["cases_included"], 240)
        self.assertEqual(r["reference_digest"], self.source["reference_digest"])
        self.assertEqual(r["source_digest"], self.source["digest"])

    def test_two_real_competing_predictions_not_fake_branch_choices(self):
        result = self.measured["dimensions"]["alternative_reasoning"]["all"]
        self.assertEqual(result["cases_with_two_branches_evaluated"], 240)
        self.assertLessEqual(result["chaos_parallel_decisions"], 240)
        self.assertGreaterEqual(result["mean_posthoc_regret_vs_best_branch"], -1e-12)
        for group in self.measured["dimensions"]["alternative_reasoning"].values():
            self.assertLessEqual(group["branch_disagreement_ge_0_10"], group["cases_with_two_branches_evaluated"])

    def test_sensor_scores_use_every_source_before_feedback(self):
        evidence = self.measured["dimensions"]["evidence_judgment"]["all"]
        self.assertEqual(evidence["sensor_observations"], 240*5)
        self.assertEqual(set(evidence["source_reliability_brier"]),
                         {"fixed_prior", "long_memory", "forgetful"})
        self.assertTrue(all(0 <= v <= 1 for v in evidence["source_reliability_brier"].values()))

    def test_uncertainty_and_decision_quality_not_collapsed(self):
        unc = self.measured["dimensions"]["uncertainty_awareness"]["all"]
        decisions = self.measured["dimensions"]["decision_quality"]["all"]
        self.assertEqual(set(unc), set(ARMS))
        self.assertEqual(set(decisions), set(ARMS))
        for arm in ARMS:
            self.assertAlmostEqual(unc[arm]["brier"],
                self.source["decision_quality"]["overall"]["arms"][arm]["brier"])
            self.assertEqual(decisions[arm]["decision_switches"],
                self.source["decision_quality"]["overall"]["arms"][arm]["decision_switches"])
            self.assertIn("0.1", decisions[arm]["decision_cost_sensitivity"])

    def test_early_late_are_descriptive(self):
        measured = self.measured["dimensions"]["learning_after_feedback"]
        self.assertEqual(measured["all"]["early_cases"], 6*2*5)
        self.assertEqual(measured["all"]["late_cases"], 6*2*5)
        self.assertIn("post_change_windows", measured["source_swap"])
        self.assertIn("caution", measured["all"])

    def test_corrupted_or_incomplete_evidence_rejected(self):
        report = {**self.source, "cases": [dict(row) for row in self.source["cases"]]}
        report["cases"][0] = {**report["cases"][0], "evidence": []}
        with self.assertRaises(ValueError):
            measure(report)
        report = {**self.source, "cases": list(self.source["cases"])[1:]}
        with self.assertRaises(ValueError):
            measure(report)

    def test_deterministic_and_verifiable_audit(self):
        result = self.measured
        self.assertEqual(result, measure(self.source))
        unsigned = {k: v for k, v in result.items() if k != "audit_sha256"}
        serial = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False)
        self.assertEqual(result["audit_sha256"], hashlib.sha256(serial.encode()).hexdigest())
        self.assertEqual(result["external_runtimes_executed"] if "external_runtimes_executed" in result
                         else self.source["external_runtimes_executed"], [])


if __name__ == "__main__":
    unittest.main()
