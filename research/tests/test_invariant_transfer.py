"""Synthetic transfer identifiability control, not a BEAN learning claim.

Run: python -m unittest -v test_invariant_transfer.py
The source correlation cannot identify the causal rule. An invariant target
mechanism with reversed nuisance correlation separates two frozen predictors.
"""
import hashlib
import json
import random
import unittest


def evaluate(seed, *, domain, n=128):
    if domain not in ('source', 'nuisance_shift', 'mechanism_shift'):
        raise ValueError('unknown predeclared domain')
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        cause = rng.randrange(2)
        token = cause if domain == 'source' else 1 - cause
        label = 1 - cause if domain == 'mechanism_shift' else cause
        rows.append((cause, token, label))
    return {'seed': seed, 'domain': domain, 'n': n,
            'lexical_correct': sum(token == label for cause, token, label in rows),
            'structural_correct': sum(cause == label for cause, token, label in rows)}


def receipt(results):
    canonical = json.dumps(results, sort_keys=True, separators=(',', ':'))
    return {'schema': 1, 'results': results,
            'sha256': hashlib.sha256(canonical.encode('utf-8')).hexdigest()}


def verified(record):
    return record['sha256'] == receipt(record['results'])['sha256']


class InvariantTransferTests(unittest.TestCase):
    def test_paired_heldout_nuisance_shift(self):
        for seed in range(1000, 1100):
            source = evaluate(seed, domain='source')
            target = evaluate(seed, domain='nuisance_shift')
            self.assertEqual((source['lexical_correct'], source['structural_correct']), (128, 128))
            self.assertEqual((target['lexical_correct'], target['structural_correct']), (0, 128))
            self.assertEqual(source['n'], target['n'])

    def test_mechanism_shift_negative_control(self):
        for seed in range(2000, 2100):
            result = evaluate(seed, domain='mechanism_shift')
            self.assertEqual((result['lexical_correct'], result['structural_correct']), (128, 0))

    def test_restart_receipt_and_tamper(self):
        original = receipt([evaluate(s, domain='nuisance_shift') for s in range(1000, 1010)])
        restored = json.loads(json.dumps(original))
        self.assertTrue(verified(restored))
        restored['results'][0]['structural_correct'] = 127
        self.assertFalse(verified(restored))

    def test_determinism_and_invalid_domain(self):
        self.assertEqual(evaluate(42, domain='nuisance_shift'), evaluate(42, domain='nuisance_shift'))
        with self.assertRaises(ValueError):
            evaluate(42, domain='unknown')


if __name__ == '__main__':
    unittest.main()
