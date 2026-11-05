"""Synthetic negative-transfer control for cross-domain lexical precedent recall.

Run: python -m unittest test_analogy_negative_transfer.py
No model, BEAN runtime, or external service is used. The same target trials
are scored under lexical-precedent and majority-baseline policies.
"""
import random
import unittest

SEED = 20261105
N = 240


def cases(seed=SEED):
    rng = random.Random(seed)
    # Identical visible terms across domains conceal reversed action semantics.
    # The target-domain signal is available to a simple domain-aware baseline.
    records = []
    for i in range(N):
        domain = 'target_reversed' if i % 2 else 'target_aligned'
        source_action = rng.randrange(2)
        target_action = source_action ^ (domain == 'target_reversed')
        records.append((domain, source_action, target_action))
    return records


def evaluate(rows, mode):
    correct = 0
    by_domain = {}
    for domain, source_action, answer in rows:
        if mode == 'lexical':
            predicted = source_action
        elif mode == 'domain_rule':
            predicted = source_action ^ (domain == 'target_reversed')
        elif mode == 'abstain':
            predicted = None
        else:
            raise ValueError(mode)
        if predicted is not None:
            correct += predicted == answer
        tally = by_domain.setdefault(domain, [0, 0])
        tally[0] += predicted == answer
        tally[1] += predicted is not None
    return correct, by_domain


class NegativeTransferTest(unittest.TestCase):
    def test_lexical_precedent_has_zero_accuracy_on_reversed_domain(self):
        _, breakdown = evaluate(cases(), 'lexical')
        self.assertEqual(breakdown['target_aligned'], [120, 120])
        self.assertEqual(breakdown['target_reversed'], [0, 120])

    def test_matched_domain_aware_control_outperforms(self):
        rows = cases()
        lexical, _ = evaluate(rows, 'lexical')
        domain_rule, _ = evaluate(rows, 'domain_rule')
        self.assertEqual((lexical, domain_rule), (120, 240))

    def test_abstention_does_not_masquerade_as_success(self):
        correct, by_domain = evaluate(cases(), 'abstain')
        self.assertEqual(correct, 0)
        self.assertEqual(sum(n for _, n in by_domain.values()), 0)

    def test_restart_replay_and_fresh_seed(self):
        original = cases()
        self.assertEqual(original, cases())
        fresh = cases(SEED + 1)
        self.assertNotEqual(original, fresh)
        self.assertEqual(evaluate(fresh, 'lexical')[0], 120)
        self.assertEqual(evaluate(fresh, 'domain_rule')[0], 240)


if __name__ == '__main__':
    unittest.main()
