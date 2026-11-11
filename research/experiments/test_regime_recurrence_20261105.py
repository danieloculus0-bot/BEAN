"""Synthetic recurrence stress test for bounded online adaptation; not BEAN runtime."""
import hashlib
import json
import random
import unittest


def evaluate(seed, period=32, n=512, window=16):
    """Predict before observing the next label; flip hidden rule every period."""
    rng = random.Random(seed)
    history = []
    correct = {"frozen": 0, "recent": 0, "cumulative": 0}
    trace = []
    for t in range(n):
        label = (t // period) % 2
        if rng.random() < 0.05:
            label ^= 1
        recent = history[-window:]
        predictions = {
            "frozen": 0,
            "recent": int(sum(recent) > len(recent) / 2) if recent else 0,
            "cumulative": int(sum(history) > len(history) / 2) if history else 0,
        }
        for key, prediction in predictions.items():
            correct[key] += int(prediction == label)
        trace.append((t, label, predictions))
        history.append(label)
    return {
        "accuracy": {k: round(v / n, 6) for k, v in correct.items()},
        "trace_sha256": hashlib.sha256(
            json.dumps(trace, sort_keys=True).encode()
        ).hexdigest(),
    }


class RecurrenceTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(evaluate(42), evaluate(42))
        self.assertNotEqual(evaluate(42)["trace_sha256"],
                            evaluate(43)["trace_sha256"])

    def test_periodic_shift_exposes_recent_window_cost(self):
        self.assertLess(evaluate(42, period=8)["accuracy"]["recent"], 0.7)

    def test_stationary_control(self):
        result = evaluate(42, period=1024)
        self.assertGreater(result["accuracy"]["frozen"], 0.9)
        self.assertGreater(result["accuracy"]["recent"], 0.9)

    def test_held_out_seeds(self):
        for seed in (1007, 2009, 3011):
            self.assertLess(evaluate(seed, period=8)["accuracy"]["recent"], 0.7)


if __name__ == "__main__":
    unittest.main()
