"""Schrodinger's Logic: delayed feedback, dual states, chaos and exact replay."""
import hashlib
import json
import math
import unittest

from experiments.cognitive_gauntlet.sensor_reliability import SensorObservation
from experiments.cognitive_gauntlet.schrodingers_logic import SchrodingersLogic
from experiments.cognitive_gauntlet.schrodinger_benchmark import benchmark, ARMS, REGIMES


class SchrodingerLogicTests(unittest.TestCase):
    def test_initially_remembers_and_preserves_both_states(self):
        model = SchrodingersLogic()
        prediction = model.forecast([SensorObservation("one", "s0", 1)])
        detail = model.diagnostics()
        self.assertEqual(detail["mode"], "remember")
        self.assertEqual(prediction, detail["long_prediction"])
        self.assertEqual(len(model.long_memory.receipts), 0)
        self.assertEqual(len(model.short_memory.receipts), 0)
        model.learn(1)
        self.assertEqual(len(model.long_memory.receipts), 1)
        self.assertEqual(len(model.short_memory.receipts), 1)

    def test_chaos_gate_uses_previous_scored_feedback(self):
        model = SchrodingersLogic(window=4, min_history=8,
                                 entry_gap=.02, exit_gap=.005,
                                 entry_advantage=.001, exit_advantage=-.005)
        # Keep source strongly correct, then reverse it. The formerly trusted
        # source becomes a source of incorrect evidence.
        modes = []
        for index in range(100):
            observation = 1
            outcome = 1 if index < 50 else 0
            model.forecast([SensorObservation(str(index), "s", observation)])
            modes.append(model.diagnostics()["mode"])
            model.learn(outcome)
        self.assertEqual(modes[:8], ["remember"]*8)
        self.assertIn("parallel_chaos", modes[50:])

    def test_no_current_truth_leak_and_strict_feedback(self):
        model = SchrodingersLogic()
        with self.assertRaises(ValueError):
            model.learn(1)
        model.forecast([SensorObservation("e1", "x", 0)])
        with self.assertRaises(ValueError):
            model.forecast([SensorObservation("e2", "x", 1)])
        with self.assertRaises(ValueError):
            model.learn(3)
        model.learn(1)
        with self.assertRaises(ValueError):
            model.forecast([SensorObservation("e1", "x", 1)])

    def test_restart_retains_both_states_and_reward_history(self):
        model = SchrodingersLogic()
        for t in range(24):
            model.forecast([SensorObservation(str(t), "x", t%2)])
            model.learn(t%3==0 and 1 or 0)
        restored = SchrodingersLogic.restore(json.loads(json.dumps(model.state())))
        self.assertEqual(restored.state(), model.state())
        item = [SensorObservation("new", "x", 1)]
        self.assertEqual(restored.forecast(item), model.forecast(item))
        self.assertEqual(restored.diagnostics(), model.diagnostics())
        restored.learn(0)
        model.learn(0)
        self.assertEqual(restored.state(), model.state())

    def test_invalid_config_and_pending_checkpoint(self):
        for settings in ({"window": 2}, {"short_decay": 1},
                         {"entry_gap": 0}, {"entry_advantage": float("nan")}):
            with self.assertRaises(ValueError):
                SchrodingersLogic(**settings)
        model = SchrodingersLogic()
        model.forecast([SensorObservation("first", "x", 0)])
        with self.assertRaises(ValueError):
            model.state()
        with self.assertRaises(ValueError):
            model.learn(True)

    def test_independent_replay_and_score_digests(self):
        kwargs = dict(seeds=2, rounds=20, first_seed=8000)
        one = benchmark(**kwargs)
        self.assertEqual(one, benchmark(**kwargs))
        self.assertEqual(len(one["cases"]), 2*20*len(REGIMES))
        self.assertEqual(one["external_runtimes_executed"], [])
        unsigned = {k: v for k, v in one.items() if k != "digest"}
        encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":"))
        self.assertEqual(one["digest"], hashlib.sha256(encoded.encode()).hexdigest())
        for regime, summary in one["scores"].items():
            rows = [r for r in one["cases"] if regime == "all" or r["regime"] == regime]
            self.assertEqual(summary["cases"], len(rows))
            self.assertEqual(summary["chaos_cases"],
                             sum(x["mode"] == "parallel_chaos" for x in rows))
            for arm in ARMS:
                self.assertAlmostEqual(summary["mse"][arm],
                    sum(x["losses"][arm] for x in rows)/len(rows))
            self.assertTrue(all(math.isfinite(x["predictions"]["schrodingers_logic"])
                                for x in rows))


if __name__ == "__main__":
    unittest.main()
