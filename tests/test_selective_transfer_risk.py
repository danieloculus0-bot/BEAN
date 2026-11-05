"""Synthetic prequential risk/coverage accounting for selective precedent use.

This does not train or evaluate BEAN's actual inference provider.
"""
import hashlib
import json
import random
import unittest
from collections import deque


def evaluate(seed, shift, n=600, window=40):
    rng = random.Random(seed)
    history = deque(maxlen=window)
    rows = []
    for t in range(n):
        confidence = 0.9 if rng.random() < .8 else .7
        prediction = rng.randrange(2)
        correct = rng.random() < (.12 if shift and t >= n // 2 else .88)
        actual = prediction if correct else 1 - prediction
        recent = sum(history) / len(history) if len(history) >= 20 else 1.
        rows.append({'t': t, 'correct': int(prediction == actual),
                     'static': confidence >= .8,
                     'adaptive': confidence >= .8 and recent >= .7})
        history.append(int(prediction == actual))  # after decisions only
    return rows


def metrics(rows, policy, start=0):
    cohort = rows[start:]
    accepted = [r for r in cohort if r[policy]]
    return {'coverage': len(accepted) / len(cohort),
            'risk': (sum(1-r['correct'] for r in accepted) / len(accepted)
                     if accepted else None),
            'accepted': len(accepted)}


class SelectiveRiskTests(unittest.TestCase):
    def test_shift_coverage_and_risk(self):
        # Abstention must not be reported as correctness; zero coverage has undefined risk.
        for seed in (17, 31, 47, 71):
            rows = evaluate(seed, True)
            s = metrics(rows, 'static', 300)
            a = metrics(rows, 'adaptive', 300)
            self.assertLess(a['coverage'], s['coverage'])
            self.assertLess(a['accepted'], s['accepted'])
            self.assertGreater(s['risk'], .65)
            self.assertEqual(len(rows), 600)

    def test_stationary_control(self):
        for seed in (17, 31, 47, 71):
            rows = evaluate(seed, False)
            a = metrics(rows, 'adaptive', 300)
            self.assertGreater(a['coverage'], .5)
            self.assertLess(a['risk'], .25)

    def test_no_future_label_leak(self):
        # A row's acceptance is calculated before its own outcome enters history.
        rows = evaluate(17, True)
        for t in range(20):
            self.assertEqual(rows[t]['adaptive'], rows[t]['static'])

    def test_deterministic_receipt_and_zero_coverage(self):
        a = evaluate(19, True)
        digest = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest(a), digest(evaluate(19, True)))
        self.assertNotEqual(digest(a), digest(evaluate(20, True)))
        self.assertIsNone(metrics([{'correct': 0, 'none': False}], 'none')['risk'])


if __name__ == '__main__':
    unittest.main()
