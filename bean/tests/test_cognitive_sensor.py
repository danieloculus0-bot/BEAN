"""Tests for delayed evidence, sensor trust adaptation and case-level receipts."""
import hashlib
import json
import unittest
from experiments.cognitive_gauntlet.sensor_reliability import OnlineSensorTrust, SensorObservation
from experiments.cognitive_gauntlet.sensor_benchmark import benchmark, REGIMES, ARMS


class SensorTrustTests(unittest.TestCase):
    def test_outcome_cannot_be_supplied_early(self):
        model = OnlineSensorTrust()
        with self.assertRaises(ValueError):
            model.learn(1)
        model.forecast([SensorObservation("e1", "s0", 1)])
        with self.assertRaises(ValueError):
            model.forecast([SensorObservation("e2", "s0", 0)])
        with self.assertRaises(ValueError):
            model.learn(2)
        model.learn(1)
        self.assertEqual(len(model.receipts), 1)

    def test_duplicate_and_invalid_evidence_rejected(self):
        model = OnlineSensorTrust()
        with self.assertRaises(ValueError):
            model.forecast([SensorObservation("x", "s0", 1),
                            SensorObservation("y", "s0", 1)])
        with self.assertRaises(ValueError):
            model.forecast([SensorObservation("x", "s0", .5)])
        model.forecast([SensorObservation("x", "s0", 1)])
        model.learn(1)
        with self.assertRaises(ValueError):
            model.forecast([SensorObservation("x", "s0", 0)])

    def test_learned_unreliable_sensor(self):
        model = OnlineSensorTrust()
        for index in range(24):
            model.forecast([SensorObservation(str(index), "bad", 0)])
            model.learn(1)
        self.assertLess(model.reliability("bad"), .2)
        self.assertGreater(model.forecast([SensorObservation("new", "bad", 0)]), .7)

    def test_checkpoint_replays_without_double_credit(self):
        model = OnlineSensorTrust(decay=.97)
        for index in range(7):
            model.forecast([SensorObservation(str(index), "s0", index % 2)])
            model.learn(1)
        recovered = OnlineSensorTrust.restore(json.loads(json.dumps(model.state())))
        self.assertEqual(model.state(), recovered.state())
        event = [SensorObservation("next", "s0", 0)]
        self.assertEqual(model.forecast(event), recovered.forecast(event))
        model.learn(1)
        recovered.learn(1)
        self.assertEqual(model.state(), recovered.state())

    def test_invalid_checkpoint_and_pending_snapshot(self):
        with self.assertRaises(ValueError):
            OnlineSensorTrust.restore({"schema": "invalid"})
        model = OnlineSensorTrust()
        model.forecast([SensorObservation("pending", "s0", 1)])
        with self.assertRaises(ValueError):
            model.state()

    def test_replay_digest_and_no_hidden_external_opponents(self):
        result = benchmark(seeds=2, rounds=20)
        self.assertEqual(result, benchmark(seeds=2, rounds=20))
        self.assertEqual(len(result["cases"]), len(REGIMES) * 2 * 20)
        self.assertEqual(result["external_runtimes_executed"], [])
        unsigned = {k: v for k, v in result.items() if k != "digest"}
        serial = json.dumps(unsigned, sort_keys=True, separators=(",", ":"))
        self.assertEqual(result["digest"], hashlib.sha256(serial.encode()).hexdigest())
        for regime, score in result["scores"].items():
            cases = [x for x in result["cases"] if regime == "all" or x["regime"] == regime]
            self.assertEqual(score["n"], len(cases))
            for arm in ARMS:
                self.assertAlmostEqual(score["mse"][arm],
                    sum(x["losses"][arm] for x in cases) / len(cases))


if __name__ == "__main__":
    unittest.main()
