"""Synthetic prequential selective-transfer test; no BEAN model is trained."""
import hashlib
import json
import random
import unittest
from collections import deque


def run(seed, shift=True, n=600, window=40):
    rng = random.Random(seed)
    history = deque(maxlen=window)
    records = []
    for t in range(n):
        confidence = 0.9 if rng.random() < 0.8 else 0.7
        prediction = rng.randrange(2)
        reversed_rule = shift and t >= n // 2
        correct = rng.random() < (0.12 if reversed_rule else 0.88)
        actual = prediction if correct else 1 - prediction
        static_accept = confidence >= 0.8
        recent_accuracy = sum(history) / len(history) if len(history) >= 20 else 1.0
        adaptive_accept = static_accept and recent_accuracy >= 0.65
        records.append((t, static_accept, adaptive_accept, int(prediction == actual)))
        history.append(int(prediction == actual))
    def metrics(idx, start):
        rows = [r for r in records if r[0] >= start]
        accepted = [r for r in rows if r[idx]]
        return {'coverage': len(accepted) / len(rows),
                'error': sum(1-r[3] for r in accepted)/len(accepted) if accepted else None,
                'accepted': len(accepted)}
    result = {'seed':seed,'shift':shift,'static':metrics(1,n//2),'adaptive':metrics(2,n//2)}
    result['sha256'] = hashlib.sha256(json.dumps(records,separators=(',',':')).encode()).hexdigest()
    return result


class CalibrationShiftTests(unittest.TestCase):
    def test_deterministic_receipts(self):
        self.assertEqual(run(17), run(17))
        self.assertNotEqual(run(17)['sha256'], run(18)['sha256'])

    def test_shift_detected_without_future_labels(self):
        for seed in (7, 17, 29, 41):
            result = run(seed)
            self.assertLess(result['adaptive']['coverage'], result['static']['coverage'] * .25)
            self.assertLess(result['adaptive']['accepted'], result['static']['accepted'])

    def test_stable_control_keeps_coverage(self):
        for seed in (7, 17, 29, 41):
            result = run(seed, shift=False)
            self.assertGreater(result['adaptive']['coverage'], .70)

    def test_no_oracle_regime_flag_in_decision(self):
        self.assertEqual(run(17, True)['seed'], run(17, False)['seed'])
        self.assertNotEqual(run(17, True)['sha256'], run(17, False)['sha256'])


if __name__ == '__main__':
    unittest.main()
