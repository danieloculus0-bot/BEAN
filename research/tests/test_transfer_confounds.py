"""Synthetic negative control: surface resemblance is not validated transfer.

Run: python -m unittest -v test_transfer_confounds.py
No BEAN runtime, model, external data, or new memory backend is used.
"""
import hashlib
import json
import random
import unittest


def evaluate(seed, reversed_rule=False, n=128):
    """Paired source/target domains; lexical token is deliberately confounded."""
    rng = random.Random(seed)
    examples = []
    for i in range(n):
        cause = rng.randrange(2)
        token = 'amber' if cause else 'violet'
        if reversed_rule:
            label = 1 - cause
        else:
            label = cause
        examples.append((token, cause, label))
    # Source lexical heuristic: amber means positive. Structural hypothesis:
    # output follows the causal bit, not the surface token.
    lexical_correct = sum((token == 'amber') == label for token, cause, label in examples)
    structural_correct = sum(cause == label for token, cause, label in examples)
    return {'seed': seed, 'reverse': reversed_rule, 'n': n,
            'lexical_correct': lexical_correct, 'structural_correct': structural_correct}


def receipt(rows):
    payload = json.dumps(rows, sort_keys=True, separators=(',', ':'))
    return {'schema': 1, 'results': rows,
            'sha256': hashlib.sha256(payload.encode()).hexdigest()}


def verify_receipt(obj):
    return receipt(obj['results'])['sha256'] == obj['sha256']


class TransferConfoundTests(unittest.TestCase):
    def test_matched_source_and_shifted_target(self):
        for seed in range(100):
            source = evaluate(seed)
            target = evaluate(seed, reversed_rule=True)
            self.assertEqual(source['lexical_correct'], 128)
            self.assertEqual(source['structural_correct'], 128)
            self.assertEqual(target['lexical_correct'], 0)
            self.assertEqual(target['structural_correct'], 0)

    def test_surface_accuracy_cannot_identify_causal_rule(self):
        # Both hypotheses agree on every source row. Source accuracy alone
        # cannot distinguish them; target reversal invalidates both.
        source = evaluate(5)
        self.assertEqual(source['lexical_correct'], source['structural_correct'])
        self.assertEqual(evaluate(5, True)['lexical_correct'], 0)

    def test_receipt_restart_and_tamper(self):
        record = receipt([evaluate(s, True) for s in range(10)])
        restored = json.loads(json.dumps(record))
        self.assertTrue(verify_receipt(restored))
        restored['results'][0]['lexical_correct'] = 1
        self.assertFalse(verify_receipt(restored))

    def test_fixed_budget_and_determinism(self):
        self.assertEqual(evaluate(42), evaluate(42))
        self.assertEqual(evaluate(42, True)['n'], evaluate(42)['n'])


if __name__ == '__main__':
    unittest.main()
