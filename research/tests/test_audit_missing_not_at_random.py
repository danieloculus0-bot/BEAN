"""Negative control: stratification cannot repair outcome-dependent audit missingness.

Synthetic research only; no BEAN Core integration. Random audits must have
known positive inclusion probabilities independent of outcome within strata.
"""
import hashlib
import json
import random
import unittest


def trial(seed, *, n=4000, biased=True):
    if n < 100 or n % 10:
        raise ValueError('n must be >=100 and divisible by ten')
    rng = random.Random(seed)
    counts = {s: [0, 0] for s in ('A', 'B')}
    actual = 0
    rows = []
    for i in range(n):
        s = 'B' if i % 5 else 'A'
        # Within each stratum both outcomes exist, unlike the prior
        # deterministic-stratum test. True error is 20% in A, 80% in B.
        error = int(rng.random() < (0.8 if s == 'B' else 0.2))
        actual += error
        # Outcome-dependent missingness is NOT random even within strata.
        p = (0.02 if error else 0.5) if biased else 0.2
        audited = rng.random() < p
        if audited:
            counts[s][0] += error
            counts[s][1] += 1
        rows.append((s, error, int(audited)))
    estimate = (sum((0.2 if s == 'A' else 0.8) * counts[s][0] / counts[s][1]
                    for s in counts) if all(v[1] for v in counts.values()) else None)
    return {'actual': actual / n, 'estimate': estimate,
            'audited': {s: v[1] for s, v in counts.items()},
            'sha256': hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()}


class MissingNotAtRandomAuditTests(unittest.TestCase):
    def test_outcome_dependent_audit_defeats_stratification(self):
        runs = [trial(seed) for seed in range(40)]
        self.assertTrue(all(x['estimate'] is not None for x in runs))
        self.assertGreater(sum(x['actual'] - x['estimate'] for x in runs) / 40, 0.25)

    def test_random_audit_control(self):
        runs = [trial(seed, biased=False) for seed in range(40)]
        self.assertLess(abs(sum(x['actual'] - x['estimate'] for x in runs) / 40), 0.025)

    def test_deterministic_receipt_and_restart(self):
        a = trial(83)
        self.assertEqual(a, json.loads(json.dumps(a)))
        self.assertEqual(a, trial(83))
        self.assertNotEqual(a['sha256'], trial(84)['sha256'])

    def test_budget_validation(self):
        for n in (0, 99, 101):
            with self.assertRaises(ValueError):
                trial(0, n=n)


if __name__ == '__main__':
    unittest.main()
