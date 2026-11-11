"""Synthetic negative control: biased feedback can defeat rolling calibration.

Research only. No BEAN inference, Core integration or independent learning.
"""
import hashlib
import json
import random
import unittest
from collections import deque


def trial(seed, selective_feedback, shifted=True, n=800, window=40):
    rng = random.Random(seed)
    recent = deque(maxlen=window)
    rows = []
    for step in range(n):
        prediction = rng.randrange(2)
        error = rng.random() < (0.85 if shifted and step >= n // 2 else 0.10)
        actual = prediction ^ int(error)
        reveal_draw = rng.random()
        # Missing-not-at-random: wrong answers rarely receive labels.
        observed = (reveal_draw < (0.03 if error else 0.95)) if selective_feedback else (reveal_draw < 0.50)
        estimated = sum(recent) / len(recent) if len(recent) >= 20 else 1.0
        accept = estimated >= 0.65
        rows.append((step, int(accept), int(prediction != actual), int(observed)))
        if observed:
            recent.append(int(not error))
    tail = rows[n // 2:]
    accepted = [r for r in tail if r[1]]
    feedback = [r for r in tail if r[3]]
    result = {
        'coverage': len(accepted) / len(tail),
        'risk': sum(r[2] for r in accepted) / len(accepted) if accepted else None,
        'feedback_rate': len(feedback) / len(tail),
        'observed_error': sum(r[2] for r in feedback) / len(feedback) if feedback else None,
        'true_error': sum(r[2] for r in tail) / len(tail),
    }
    result['trace_sha256'] = hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()
    return result


class FeedbackSelectionBiasTests(unittest.TestCase):
    def test_deterministic_and_fresh_seeds(self):
        self.assertEqual(trial(101, True), trial(101, True))
        self.assertNotEqual(trial(101, True)['trace_sha256'], trial(102, True)['trace_sha256'])

    def test_biased_feedback_hides_shift(self):
        for seed in (101, 203, 307, 409):
            biased = trial(seed, True)
            unbiased = trial(seed, False)
            self.assertGreater(biased['coverage'], 0.90)
            self.assertLess(unbiased['coverage'], 0.25)
            self.assertGreater(biased['risk'], 0.75)
            self.assertLess(biased['observed_error'], 0.30)
            self.assertAlmostEqual(biased['true_error'], unbiased['true_error'])

    def test_stable_control_no_spurious_collapse(self):
        for seed in (101, 203, 307, 409):
            self.assertGreater(trial(seed, False, shifted=False)['coverage'], 0.85)

    def test_no_feedback_is_not_evidence_of_success(self):
        result = trial(101, True)
        self.assertLess(result['feedback_rate'], 0.20)
        self.assertGreater(result['true_error'], result['observed_error'] + 0.60)


if __name__ == '__main__':
    unittest.main()
