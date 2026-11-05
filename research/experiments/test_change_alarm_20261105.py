"""Synthetic sequential change-point probe; no BEAN Core learning claim.

Three predictors see identical post-prediction feedback. This is a toy
control, not evidence of transferable intelligence. Run: python -m unittest
discover -s research/experiments -p 'test_change_alarm_20261105.py' -v
"""
import random
import unittest


def stream(seed, shift, n=240):
    rng = random.Random(seed)
    return [int(rng.random() < (0.85 if (not shift or i < n // 2) else 0.15))
            for i in range(n)]


def evaluate(seed, shift):
    labels = stream(seed, shift)
    history = []
    errors = {'frozen': 0, 'window': 0, 'alarm': 0}
    alarms = []
    alarm_state = 1
    streak = 0
    predictions = {k: [] for k in errors}
    for i, y in enumerate(labels):
        frozen = 1
        recent = history[-16:]
        window = int(sum(recent) >= len(recent) / 2) if recent else 1
        choices = {'frozen': frozen, 'window': window, 'alarm': alarm_state}
        for name, value in choices.items():
            predictions[name].append(value)
            errors[name] += value != y
        # Feedback is observed only AFTER every predictor has committed.
        history.append(y)
        streak = streak + 1 if y != alarm_state else 0
        if streak >= 5:
            alarm_state = 1 - alarm_state
            alarms.append(i)
            streak = 0
    return {'accuracy': {k: 1 - errors[k] / len(labels) for k in errors},
            'alarms': alarms, 'predictions': predictions}


class ProbeTests(unittest.TestCase):
    def test_deterministic_replay(self):
        self.assertEqual(evaluate(19, True), evaluate(19, True))

    def test_no_future_label_leakage(self):
        stable, shifted = evaluate(19, False), evaluate(19, True)
        for name in stable['predictions']:
            self.assertEqual(stable['predictions'][name][:120],
                             shifted['predictions'][name][:120])

    def test_shift_and_no_shift_controls(self):
        for seed in (19, 47, 101, 809):
            shifted, stable = evaluate(seed, True), evaluate(seed, False)
            self.assertGreater(shifted['accuracy']['window'],
                               shifted['accuracy']['frozen'])
            self.assertGreater(stable['accuracy']['frozen'], 0.75)


if __name__ == '__main__':
    unittest.main()
