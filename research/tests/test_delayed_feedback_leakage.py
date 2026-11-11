"""Synthetic prequential test: delayed outcome labels must not leak into decisions.

Research-only negative control. No production BEAN Core changes or AGI claim.
"""
import hashlib
import json
import random
import unittest


def stream(seed, n=600, delay=12):
    rng = random.Random(seed)
    return [{"t": t, "label": int(rng.random() < (0.85 if t < n // 2 else 0.15)),
             "reveal_at": t + delay} for t in range(n)]


def evaluate(rows, mode="causal", window=40):
    if mode not in ("causal", "leaky", "static") or window < 1:
        raise ValueError("invalid mode/window")
    predictions = []
    for row in rows:
        t = row["t"]
        if mode == "static":
            prediction = 1
        else:
            observed = [r["label"] for r in rows if
                        (r["reveal_at"] <= t if mode == "causal" else r["t"] <= t)]
            recent = observed[-window:]
            prediction = int(sum(recent) * 2 >= len(recent)) if recent else 1
        predictions.append(prediction)
    receipt = {"mode": mode, "correct": sum(p == r["label"] for p, r in zip(predictions, rows)),
               "total": len(rows), "predictions": predictions}
    receipt["sha256"] = hashlib.sha256(json.dumps(receipt, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()
    return receipt


class DelayedFeedbackLeakage(unittest.TestCase):
    def test_future_labels_cannot_change_past_decisions(self):
        rows = stream(73)
        mutated = [dict(r) for r in rows]
        for r in mutated:
            if r["reveal_at"] > 300:
                r["label"] ^= 1
        self.assertEqual(evaluate(rows)["predictions"][:301],
                         evaluate(mutated)["predictions"][:301])

    def test_leaky_oracle_is_distinguishable(self):
        rows = stream(5)
        self.assertNotEqual(evaluate(rows)["predictions"],
                            evaluate(rows, "leaky")["predictions"])

    def test_shifted_heldout_comparison(self):
        gains = []
        for seed in range(1000, 1020):
            rows = stream(seed)
            gains.append(evaluate(rows)["correct"] - evaluate(rows, "static")["correct"])
        self.assertGreater(sum(gains), 0)

    def test_restart_replay_and_hash(self):
        rows = stream(91)
        self.assertEqual(evaluate(rows), evaluate(json.loads(json.dumps(rows))))
        receipt = evaluate(rows)
        body = {k: v for k, v in receipt.items() if k != "sha256"}
        self.assertEqual(receipt["sha256"], hashlib.sha256(json.dumps(
            body, sort_keys=True, separators=(",", ":")).encode()).hexdigest())

    def test_zero_delay_and_invalid_inputs(self):
        rows = stream(7, delay=0)
        self.assertEqual(evaluate(rows)["predictions"], evaluate(rows, "leaky")["predictions"])
        with self.assertRaises(ValueError):
            evaluate(rows, window=0)
        with self.assertRaises(ValueError):
            evaluate(rows, mode="oracle")


if __name__ == "__main__":
    unittest.main()
