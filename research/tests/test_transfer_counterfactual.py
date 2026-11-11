"""Synthetic falsification test: lexical similarity is not validated transfer.

Research only. No model calls, BEAN Core mutation, or claimed learned capability.
Each task has a latent rule; source and target share a vocabulary but may
have different causal rules. Target feedback is available only after prediction.
"""
import hashlib
import json
import random
import unittest


def evaluate(seed, *, n=240, target_rule='same', probes=12):
    """Compare lexical transfer, abstaining baseline, and probed rule transfer.

    Source rule: label = first bit XOR second bit. In inverted targets, label
    is its complement. All examples use identical token vocabulary, so
    lexical resemblance is uninformative about the causal change.
    """
    if target_rule not in ('same', 'inverted') or n < 2 or not 0 <= probes < n:
        raise ValueError('invalid experiment parameters')
    rng = random.Random(seed)
    inputs = [(rng.randrange(2), rng.randrange(2)) for _ in range(n)]
    def source(x):
        return x[0] ^ x[1]
    def truth(x):
        return source(x) ^ int(target_rule == 'inverted')
    # Probe labels are acquired before evaluation, never from held-out outcomes.
    observed = [truth(x) for x in inputs[:probes]]
    hypotheses = [lambda x: source(x), lambda x: 1 - source(x)]
    errors = [sum(int(h(x) != y) for x, y in zip(inputs[:probes], observed)) for h in hypotheses]
    selected = None if not probes or errors[0] == errors[1] else min(range(2), key=lambda i: errors[i])
    heldout = inputs[probes:]
    actual = [truth(x) for x in heldout]
    lexical = [source(x) for x in heldout]
    adapted = None if selected is None else [hypotheses[selected](x) for x in heldout]
    receipt = {
        'seed': seed, 'n': n, 'target_rule': target_rule, 'probes': probes,
        'lexical_accuracy': sum(a == b for a, b in zip(lexical, actual)) / len(actual),
        'probe_selected_rule': selected,
        'adapted_accuracy': None if adapted is None else sum(a == b for a, b in zip(adapted, actual)) / len(actual),
        'probe_error_counts': errors,
        'heldout_count': len(heldout),
        'baseline_abstains': True,
        'limitation': 'binary XOR toy; privileged known hypothesis set; no novel rule induction',
    }
    encoded = json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode()
    return receipt, hashlib.sha256(encoded).hexdigest()


class TransferCounterfactualTests(unittest.TestCase):
    def test_shift_reverses_lexical_transfer(self):
        for seed in range(40):
            r, _ = evaluate(seed, target_rule='inverted')
            self.assertEqual(r['lexical_accuracy'], 0)
            self.assertEqual(r['adapted_accuracy'], 1)
            self.assertEqual(r['probe_selected_rule'], 1)

    def test_stationary_control(self):
        for seed in range(40, 80):
            r, _ = evaluate(seed)
            self.assertEqual(r['lexical_accuracy'], 1)
            self.assertEqual(r['adapted_accuracy'], 1)
            self.assertEqual(r['probe_selected_rule'], 0)

    def test_no_feedback_does_not_claim_transfer(self):
        r, _ = evaluate(17, target_rule='inverted', probes=0)
        self.assertIsNone(r['adapted_accuracy'])
        self.assertIsNone(r['probe_selected_rule'])
        self.assertTrue(r['baseline_abstains'])

    def test_heldout_labels_do_not_select_rule(self):
        a, _ = evaluate(2, target_rule='inverted', probes=12)
        b, _ = evaluate(2, target_rule='inverted', probes=12, n=500)
        self.assertEqual(a['probe_selected_rule'], b['probe_selected_rule'])
        self.assertEqual(a['probe_error_counts'], b['probe_error_counts'])

    def test_reproducible_receipt_and_invalid_inputs(self):
        self.assertEqual(evaluate(77), evaluate(77))
        for args in ({'n': 1}, {'probes': 240}, {'probes': -1}, {'target_rule': 'unknown'}):
            with self.assertRaises(ValueError):
                evaluate(77, **args)


if __name__ == '__main__':
    unittest.main()
