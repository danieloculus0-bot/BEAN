"""Synthetic fixed-budget online selection between supplied mechanism hypotheses.

Research-only: candidate selection is not causal discovery, learned abstraction,
or a claim of transfer. No Core runtime behavior is changed.
"""
import hashlib
import json
import random
import unittest


def trial(seed, reverse=False, budget=12, n_test=128):
    rng = random.Random(seed)
    probes = [(rng.randrange(2), rng.randrange(2)) for _ in range(budget)]
    test = [(rng.randrange(2), rng.randrange(2)) for _ in range(n_test)]

    def label(pair):
        return pair[0] ^ int(reverse)

    # Equal feedback budget for both candidate hypotheses.
    scores = [sum((pair[0] ^ i) == label(pair) for pair in probes)
              for i in (0, 1)]
    choice = None if scores[0] == scores[1] else (
        0 if scores[0] > scores[1] else 1)
    return {
        "structural": sum(pair[0] == label(pair) for pair in test),
        "lexical": sum(pair[1] == label(pair) for pair in test),
        "adaptive": (sum((pair[0] ^ choice) == label(pair) for pair in test)
                     if choice is not None else None),
        "choice": choice,
        "probe_scores": scores,
    }


def experiment():
    records = [
        {"seed": seed, "mechanism_reversed": reverse,
         **trial(seed, reverse)}
        for reverse in (False, True)
        for seed in range(1000, 1200)
    ]
    payload = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return records, hashlib.sha256(payload.encode()).hexdigest()


class MechanismSelectionTests(unittest.TestCase):
    def test_determinism_and_receipt(self):
        self.assertEqual(experiment(), experiment())
        rows, digest = experiment()
        self.assertEqual(len(rows), 400)
        self.assertEqual(len(digest), 64)
        altered = json.dumps(rows[:-1], sort_keys=True, separators=(",", ":"))
        self.assertNotEqual(hashlib.sha256(altered.encode()).hexdigest(), digest)

    def test_frozen_structural_rule_fails_on_reversal(self):
        self.assertTrue(all(trial(s, True)["structural"] < 128
                            for s in range(1000, 1200)))

    def test_predefined_adaptation_is_not_discovery(self):
        rows, _ = experiment()
        self.assertTrue(all(r["adaptive"] == 128 for r in rows))
        self.assertTrue(all(r["choice"] == int(r["mechanism_reversed"])
                            for r in rows))

    def test_zero_budget_abstains(self):
        self.assertIsNone(trial(42, budget=0)["adaptive"])


if __name__ == "__main__":
    unittest.main()
