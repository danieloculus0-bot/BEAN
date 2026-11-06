"""Synthetic noisy-feedback and out-of-hypothesis transfer falsification.

Research-only: no Core wiring or neural inference. Target probes precede held-out
outcomes. Competing known hypotheses are XOR and inverted XOR. An unseen rule
(first-bit only) must not be misreported as learned transfer.
"""
import hashlib
import json
import math
import random
import unittest


def evaluate(seed, rule='inverted', probes=48, noise=0.1, n=256, threshold=0.68):
    if rule not in ('same', 'inverted', 'novel') or not 0 <= noise < 0.5 or not 0 <= probes < n or not 0.5 < threshold < 1:
        raise ValueError('invalid parameters')
    rng = random.Random(seed)
    xs = [(rng.randrange(2), rng.randrange(2)) for _ in range(n)]
    def label(x):
        v = x[0] ^ x[1]
        return v if rule == 'same' else 1-v if rule == 'inverted' else x[0]
    # Separate probe noise stream, not drawn from held-out outcomes.
    probe_rng = random.Random(seed ^ 0x5A5A)
    observed = [label(x) ^ int(probe_rng.random() < noise) for x in xs[:probes]]
    matches = [sum((x[0]^x[1]^flip) == y for x,y in zip(xs[:probes],observed)) for flip in (0,1)]
    # A two-sided Hoeffding union bound over both candidate accuracies.
    radius = math.sqrt(math.log(4 / 0.05) / (2*probes)) if probes else 1
    best = max(range(2),key=lambda i:matches[i]) if probes else None
    lower = matches[best]/probes-radius if probes else 0
    chosen = best if lower >= threshold else None
    held = xs[probes:]
    truth = [label(x) for x in held]
    lexical = [x[0]^x[1] for x in held]
    adapted = [(x[0]^x[1]^chosen) for x in held] if chosen is not None else None
    receipt = {'seed':seed,'rule':rule,'probes':probes,'noise':noise,'n':n,
      'matches':matches,'lower_bound':round(lower,8),'threshold':threshold,
      'selected':chosen,'coverage':int(chosen is not None),
      'lexical_accuracy':sum(a==b for a,b in zip(lexical,truth))/len(truth),
      'adapted_accuracy':None if adapted is None else sum(a==b for a,b in zip(adapted,truth))/len(truth),
      'limitation':'known two-hypothesis set; synthetic independent probe noise; no learned new rule'}
    digest=hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return receipt,digest


class NoisyTransferTests(unittest.TestCase):
    def test_known_rules_with_noise(self):
        for rule in ('same','inverted'):
            results=[evaluate(seed,rule=rule,probes=96) for seed in range(40)]
            self.assertGreaterEqual(sum(r['selected']==int(rule=='inverted') for r,_ in results),35)
            self.assertTrue(all(r['adapted_accuracy']==1 for r,_ in results if r['selected'] is not None))

    def test_novel_rule_abstains_often(self):
        results=[evaluate(seed,rule='novel',probes=96) for seed in range(80,160)]
        self.assertGreaterEqual(sum(r['selected'] is None for r,_ in results),75)
        self.assertTrue(all(r['lexical_accuracy']<0.65 for r,_ in results))

    def test_sparse_feedback_abstains(self):
        self.assertIsNone(evaluate(1,probes=0)[0]['selected'])
        self.assertIsNone(evaluate(1,probes=4)[0]['selected'])

    def test_holdout_cannot_change_selection(self):
        a,_=evaluate(3,probes=96,n=256)
        b,_=evaluate(3,probes=96,n=512)
        self.assertEqual((a['matches'],a['selected']),(b['matches'],b['selected']))

    def test_receipt_and_invalid(self):
        self.assertEqual(evaluate(42),evaluate(42))
        for kw in ({'noise':0.5},{'probes':256},{'rule':'other'},{'threshold':1}):
            with self.assertRaises(ValueError):evaluate(42,**kw)

if __name__=='__main__':unittest.main()
