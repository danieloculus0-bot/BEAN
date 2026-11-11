"""Research-only: noisy feedback and delayed mechanism change under fixed budgets.

Two supplied binary hypotheses; this is adaptation to known alternatives, not
causal discovery. Independent target labels are never used for selection.
"""
import hashlib
import json
import random
import unittest

SEEDS = 100
PROB_FLIP = 0.15
WINDOW = 11
BUDGET = 40


def trial(seed, change=True):
    rng = random.Random(seed)
    # Paired training stream with label noise; no test labels used for fitting.
    observations = [(rng.randrange(2), rng.random() < PROB_FLIP) for _ in range(BUDGET)]
    results = {"window": [], "cumulative": [], "frozen": []}
    history = []
    for t, (bit, flipped) in enumerate(observations):
        regime = int(change and t >= BUDGET // 2)
        label = bit ^ regime ^ int(flipped)
        history.append((bit, label))
        if t < BUDGET // 2:
            continue
        # Same observations, same hypothesis class, no access to evaluation labels.
        for method in results:
            sample = history[-WINDOW:] if method == "window" else history
            inferred = 0 if method == "frozen" else int(sum(b != y for b, y in sample) > len(sample) / 2)
            results[method].append(int(inferred == regime))
    return {k: sum(v) for k, v in results.items()}


def run():
    rows = [trial(seed) for seed in range(SEEDS)]
    totals = {k: sum(row[k] for row in rows) for k in ("window", "cumulative", "frozen")}
    receipt = {"schema": 1, "seeds": SEEDS, "budget": BUDGET, "window": WINDOW,
               "noise": PROB_FLIP, "metric": "correct inferred mechanism after switch, including adaptation delay",
               "denominator": SEEDS * (BUDGET // 2), "totals": totals}
    payload = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    return receipt, hashlib.sha256(payload.encode()).hexdigest()


class NoisyShiftTests(unittest.TestCase):
    def test_determinism(self):
        self.assertEqual(run(), run())

    def test_adaptation_against_controls(self):
        receipt, _ = run()
        scores = receipt["totals"]
        self.assertGreater(scores["window"], scores["frozen"])
        self.assertGreater(scores["window"], scores["cumulative"])

    def test_negative_control_no_shift(self):
        self.assertEqual(trial(5, change=False)["frozen"], 20)

    def test_receipt_tampering(self):
        receipt, digest = run()
        copy = json.loads(json.dumps(receipt))
        copy["totals"]["window"] += 1
        self.assertNotEqual(hashlib.sha256(json.dumps(copy, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
