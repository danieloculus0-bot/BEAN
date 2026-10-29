"""Evidence and scoring checks for the isolated cognitive gauntlet."""
import hashlib
import json
import unittest

from experiments.cognitive_gauntlet.arena import run
from experiments.cognitive_gauntlet.cognition import Evidence, RevisableBelief
from experiments.cognitive_gauntlet.paired_baseline import score


class TestPaired(unittest.TestCase):
    def test_repeatable(self):
        self.assertEqual(score(7, 20), score(7, 20))

    def test_full_history(self):
        self.assertEqual(len(score(7, 20)["cases"]), 20)

    def test_no_external_wins(self):
        self.assertEqual(score(7, 20)["external_agents_executed"], [])

    def test_duplicate_evidence_rejected(self):
        model = RevisableBelief()
        model.observe(Evidence("event-1", "sensor-a", 1., .65))
        with self.assertRaises(ValueError):
            model.observe(Evidence("event-1", "sensor-a", 0., .65))

    def test_source_updates_retained_but_not_double_counted(self):
        model = RevisableBelief()
        model.observe(Evidence("one", "same-origin", 1., .65))
        model.observe(Evidence("two", "same-origin", 0., .65))
        self.assertEqual(len(model.history), 2)
        self.assertLess(model.prediction(), .5)

    def test_invalid_evidence_rejected(self):
        model = RevisableBelief()
        with self.assertRaises(ValueError):
            model.observe(Evidence("bad", "sensor", float("nan"), .65))

    def test_arena_seeded_replay_and_digest(self):
        first = run(seeds=2, rounds=9)
        self.assertEqual(first, run(seeds=2, rounds=9))
        self.assertEqual(len(first["cases"]), 54)
        self.assertEqual(first["external_runtimes_executed"], [])
        self.assertIn("rapid_drift", first["scoreboard"])
        payload = {k: v for k, v in first.items() if k != "evidence_sha256"}
        serial = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        self.assertEqual(first["evidence_sha256"], hashlib.sha256(serial.encode()).hexdigest())

    def test_scores_reconcile_with_every_case(self):
        report = run(seeds=3, rounds=11)
        for scenario, summary in report["scoreboard"].items():
            rows = [row for row in report["cases"] if row["scenario"] == scenario]
            self.assertEqual(summary["n"], len(rows))
            for arm in ("bean_revision", "bean_latest"):
                self.assertAlmostEqual(summary["mse"][arm],
                                       sum(row["squared_error"][arm] for row in rows) / len(rows))
            self.assertEqual(summary["revision_better_cases"] +
                             summary["revision_worse_cases"] + summary["ties"], len(rows))


if __name__ == "__main__":
    unittest.main()
