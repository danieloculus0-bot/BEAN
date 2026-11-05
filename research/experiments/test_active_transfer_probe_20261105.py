"""Synthetic active-probe transfer control; no BEAN runtime or AGI claim.

A source domain gives a binary rule. A target may preserve or invert it.
An agent may pay for ONE labeled target probe before a held-out batch.
Compare blind transfer, random guessing, and a probe-guided policy.
"""
import hashlib
import json
import random
import unittest


def trial(seed, n=200, shift=False, noise=0.0):
    rng = random.Random(seed)
    source = rng.randrange(2)
    target = source ^ int(shift)
    probe_x = rng.randrange(2)
    probe_y = probe_x ^ target
    inferred = probe_x ^ probe_y
    rows = []
    for _ in range(n):
        x = rng.randrange(2)
        true_y = x ^ target
        if rng.random() < noise:
            true_y ^= 1
        rows.append((x, true_y))
    guesses = [rng.randrange(2) for _ in rows]
    scores = {
        "blind_source": sum((x ^ source) == y for x, y in rows) / n,
        "one_probe": sum((x ^ inferred) == y for x, y in rows) / n,
        "random": sum(g == y for g, (_, y) in zip(guesses, rows)) / n,
    }
    receipt = hashlib.sha256(json.dumps({
        "seed": seed, "shift": shift, "noise": noise, "source": source,
        "probe": [probe_x, probe_y], "rows": rows, "scores": scores,
    }, sort_keys=True).encode()).hexdigest()
    return scores, receipt


class ActiveTransferProbeTests(unittest.TestCase):
    def test_heldout_shift_improves_over_blind_transfer(self):
        for seed in (11, 29, 67, 103, 211):
            score, _ = trial(seed, shift=True)
            self.assertEqual(score["blind_source"], 0)
            self.assertEqual(score["one_probe"], 1)

    def test_no_shift_preserves_source_skill(self):
        for seed in (13, 37, 79):
            score, _ = trial(seed)
            self.assertEqual(score["blind_source"], 1)
            self.assertEqual(score["one_probe"], 1)

    def test_noisy_holdout_and_replay(self):
        a = trial(20261105, n=400, shift=True, noise=.15)
        self.assertEqual(a, trial(20261105, n=400, shift=True, noise=.15))
        self.assertGreater(a[0]["one_probe"], a[0]["blind_source"])
        self.assertGreater(a[0]["one_probe"], a[0]["random"])

    def test_probe_is_excluded_from_holdout(self):
        a, _ = trial(53, n=1, shift=True)
        self.assertEqual(a["one_probe"], 1)
        self.assertEqual(a["blind_source"], 0)


if __name__ == "__main__":
    unittest.main()
