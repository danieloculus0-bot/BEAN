"""Causal and regression checks for delayed-outcome dependency inference."""
import hashlib
import copy
import json
import unittest
from experiments.cognitive_gauntlet.sensor_reliability import SensorObservation
from experiments.cognitive_gauntlet.sensor_dependency import OnlineDependencyLearner
from experiments.cognitive_gauntlet.sensor_dependency_benchmark import benchmark, REGIMES, ARMS


class SensorDependencyTests(unittest.TestCase):
    def test_learns_shared_errors_only_after_feedback(self):
        model = OnlineDependencyLearner(decay=1, min_samples=20,
                                        min_coerrors=3, min_excess=.10)
        for step in range(40):
            truth = step % 2
            wrong = step % 4 == 0
            obs = [SensorObservation(f"{step}:{i}", f"s{i}",
                                     1 - truth if wrong and i < 2 else truth)
                   for i in range(3)]
            model.forecast(obs)
            if step == 0:
                self.assertNotEqual(model.last_groups["s0"], model.last_groups["s1"])
            model.learn(truth)
        groups = model.inferred_groups(["s0", "s1", "s2"])
        self.assertEqual(groups["s0"], groups["s1"])
        self.assertNotEqual(groups["s0"], groups["s2"])

    def test_independent_errors_do_not_group(self):
        model = OnlineDependencyLearner(decay=1)
        for step in range(60):
            truth = step % 2
            obs = [SensorObservation(f"{step}:{i}", f"s{i}",
                    1 - truth if (step + i * 7) % 5 == 0 else truth)
                   for i in range(3)]
            model.forecast(obs)
            model.learn(truth)
        self.assertEqual(len(set(model.inferred_groups(["s0", "s1", "s2"]).values())), 3)

    def test_missing_feedback_does_not_infer_dependencies(self):
        model = OnlineDependencyLearner()
        for step in range(50):
            obs = [SensorObservation(f"{step}:{i}", f"s{i}", 0) for i in range(3)]
            model.forecast(obs)
            model.skip_feedback(reason="unavailable")
        self.assertFalse(model.pairs)
        self.assertEqual(len(set(model.last_groups.values())), 3)

    def test_invalid_budget_and_feedback_cannot_consume_ids(self):
        model = OnlineDependencyLearner(max_sources=2, max_pairs=1)
        obs = [SensorObservation("a", "s0", 1), SensorObservation("b", "s1", 0)]
        with self.assertRaises(ValueError):
            model.forecast(obs + [SensorObservation("c", "s2", 1)])
        model.forecast(obs)
        with self.assertRaises(ValueError):
            model.learn(7)
        self.assertFalse(model.pairs)
        model.learn(1)
        self.assertEqual(len(model.pairs), 1)
        with self.assertRaises(ValueError):
            model.forecast(obs)


    def test_checkpoint_continuation_matches_uninterrupted_heldout(self):
        # Frozen policy and disjoint deterministic observations; no outcome is
        # revealed until after both forecasts, including missing-feedback cases.
        uninterrupted = OnlineDependencyLearner(min_samples=10, min_coerrors=2,
                                                min_excess=.05)
        restarted = OnlineDependencyLearner(min_samples=10, min_coerrors=2,
                                           min_excess=.05)
        for step in range(90):
            truth = (step // 7) % 2
            observations = [
                SensorObservation(f"restart:{step}:{i}", f"s{i}",
                                  truth ^ int((step % 9 == 0 and i < 2)
                                             or (i == 2 and step % 13 == 0)))
                for i in range(3)
            ]
            self.assertEqual(uninterrupted.forecast(observations),
                             restarted.forecast(observations))
            self.assertEqual(uninterrupted.last_groups, restarted.last_groups)
            if step % 11 == 0:
                uninterrupted.skip_feedback(reason="host_unavailable")
                restarted.skip_feedback(reason="host_unavailable")
            else:
                uninterrupted.learn(truth)
                restarted.learn(truth)
            if step in (29, 59):
                snapshot = restarted.state()
                restarted = OnlineDependencyLearner.restore(snapshot)
                self.assertEqual(snapshot, restarted.state())
        self.assertEqual(uninterrupted.state(), restarted.state())

    def test_checkpoint_rejects_corruption_and_pending_feedback(self):
        model = OnlineDependencyLearner()
        observations = [SensorObservation("checkpoint:a", "s0", 1),
                        SensorObservation("checkpoint:b", "s1", 0)]
        model.forecast(observations)
        with self.assertRaises(ValueError):
            model.state()
        model.learn(1)
        original = model.state()
        self.assertEqual(OnlineDependencyLearner.restore(original).state(), original)
        corruptions = []
        wrong = copy.deepcopy(original)
        wrong["pairs"][0]["both_wrong"] = 2.0
        corruptions.append(wrong)
        wrong = copy.deepcopy(original)
        wrong["pairs"].append(copy.deepcopy(wrong["pairs"][0]))
        corruptions.append(wrong)
        wrong = copy.deepcopy(original)
        wrong["pairs"][0]["sources"] = ["s1", "s0"]
        corruptions.append(wrong)
        wrong = copy.deepcopy(original)
        wrong["pairs"][0]["n"] = float("nan")
        corruptions.append(wrong)
        wrong = copy.deepcopy(original)
        wrong["trust"]["seen_ids"] = []
        corruptions.append(wrong)
        wrong = copy.deepcopy(original)
        wrong["schema"] = "other"
        corruptions.append(wrong)
        for snapshot in corruptions:
            with self.subTest(snapshot=snapshot.get("schema")):
                with self.assertRaises(ValueError):
                    OnlineDependencyLearner.restore(snapshot)
        self.assertEqual(model.state(), original)


    def test_verified_unrelated_feedback_ages_stale_pairs(self):
        model = OnlineDependencyLearner(decay=.9, min_samples=5,
                                        min_coerrors=2, min_excess=.10)
        for step in range(60):
            truth = step % 2
            wrong = step % 3 == 0
            obs = [SensorObservation(f"warm:{step}:{i}", f"s{i}",
                                     1 - truth if wrong and i < 2 else truth)
                   for i in range(3)]
            model.forecast(obs)
            model.learn(truth)
        self.assertEqual(model.inferred_groups(["s0", "s1"])["s0"],
                         model.inferred_groups(["s0", "s1"])["s1"])
        before = model.pairs[("s0", "s1")].n
        for step in range(60, 120):
            truth = step % 2
            obs = [SensorObservation(f"gap:{step}:{i}", f"s{i}", truth)
                   for i in (2, 3)]
            model.forecast(obs)
            model.learn(truth)
            if step == 89:
                model = OnlineDependencyLearner.restore(model.state())
        self.assertLess(model.pairs[("s0", "s1")].n, before * .01)
        groups = model.inferred_groups(["s0", "s1"])
        self.assertNotEqual(groups["s0"], groups["s1"])

    def test_missing_feedback_does_not_age_absent_pairs(self):
        model = OnlineDependencyLearner(decay=.9, min_samples=5,
                                        min_coerrors=2, min_excess=.10)
        for step in range(60):
            truth = step % 2
            obs = [SensorObservation(f"label:{step}:{i}", f"s{i}",
                                     1 - truth if step % 3 == 0 else truth)
                   for i in (0, 1)]
            model.forecast(obs)
            model.learn(truth)
        original = copy.deepcopy(model.state()["pairs"])
        for step in range(60, 120):
            model.forecast([SensorObservation(f"missing:{step}:{i}",
                                              f"s{i}", step % 2)
                            for i in (2, 3)])
            model.skip_feedback(reason="no_attested_outcome")
        self.assertEqual(model.state()["pairs"], original)

    def test_absence_shift_heldout_receipts_and_controls(self):
        from experiments.cognitive_gauntlet.sensor_dependency_absence_benchmark import (
            benchmark as absence_benchmark, REGIMES as absence_regimes)
        report = absence_benchmark(seeds=2, warmup=60, absence=60,
                                   return_steps=60)
        self.assertEqual(report, absence_benchmark(
            seeds=2, warmup=60, absence=60, return_steps=60))
        self.assertEqual(len(report["cases"]), 3 * 2 * 180)
        payload = {k: v for k, v in report.items() if k != "digest"}
        self.assertEqual(report["digest"], hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()).hexdigest())
        for regime in absence_regimes:
            for phase in ("training", "absence", "return"):
                rows = [r for r in report["cases"]
                        if r["regime"] == regime and r["phase"] == phase]
                score = report["scores"][regime][phase]
                self.assertEqual(score["n"], len(rows))
                self.assertEqual(score["missing"], sum(
                    not r["feedback_available"] for r in rows))
                for arm in ("frozen_pair_only", "global_verified_decay"):
                    self.assertAlmostEqual(score["mse"][arm], sum(
                        r["losses"][arm] for r in rows) / len(rows))
                if phase == "training" or regime == "unlabeled_absence":
                    for row in rows:
                        self.assertEqual(row["predictions"]["frozen_pair_only"],
                                         row["predictions"]["global_verified_decay"])

    def test_heldout_receipts_and_negative_controls(self):
        report = benchmark(seeds=2, rounds=45)
        self.assertEqual(report, benchmark(seeds=2, rounds=45))
        self.assertEqual(len(report["cases"]), len(REGIMES) * 2 * 45)
        payload = {k: v for k, v in report.items() if k != "digest"}
        self.assertEqual(report["digest"], hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()).hexdigest())
        for regime, score in report["scores"].items():
            rows = [r for r in report["cases"] if regime == "all" or r["regime"] == regime]
            self.assertEqual(score["n"], len(rows))
            self.assertEqual(score["missing"], sum(not r["feedback_available"] for r in rows))
            for arm in ARMS:
                self.assertAlmostEqual(score["mse"][arm], sum(r["losses"][arm] for r in rows) / len(rows))
            if regime == "independent":
                for row in rows:
                    self.assertEqual(row["predictions"]["ungrouped"],
                                     row["predictions"]["oracle_grouped"])


if __name__ == "__main__":
    unittest.main()
