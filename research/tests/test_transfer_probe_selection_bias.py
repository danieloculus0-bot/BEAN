"""Negative control: adaptive probe selection can defeat IID confidence claims.

Synthetic research only; does not modify BEAN Core or claim general transfer.
"""
import hashlib
import json
import math
import random
import unittest


def trial(seed, n_probe=96, n_test=512):
    rng = random.Random(seed)
    # Novel target rule y=x0. An active sampler repeatedly asks only x1=0.
    # On those probes, XOR is perfectly predictive despite being wrong elsewhere.
    probes = [(rng.randrange(2), 0) for _ in range(n_probe)]
    test = [(rng.randrange(2), rng.randrange(2)) for _ in range(n_test)]
    labels = [x[0] for x in probes]
    matches = [sum((x[0] ^ x[1] ^ flip) == y for x,y in zip(probes,labels)) for flip in (0,1)]
    radius = math.sqrt(math.log(4 / .05) / (2*n_probe))
    best = max(range(2),key=lambda i:matches[i])
    accepted = matches[best]/n_probe-radius >= .68
    accuracy = sum((x[0]^x[1]^best)==x[0] for x in test)/n_test
    # Explicit support coverage, unlike a misleading IID confidence interval.
    support = len(set(probes)) / 4
    receipt = {'seed':seed,'probe_count':n_probe,'test_count':n_test,'matches':matches,
               'selected':best if accepted else None,'heldout_accuracy':accuracy,
               'support_coverage':support,'assumption_violation':'probes exclude x1=1'}
    digest=hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return receipt,digest

class ProbeSelectionBiasTests(unittest.TestCase):
    def test_false_confidence_under_unrepresentative_probes(self):
        results=[trial(seed)[0] for seed in range(100)]
        self.assertTrue(all(r['selected']==0 for r in results))
        self.assertTrue(all(r['support_coverage']==.5 for r in results))
        self.assertLess(sum(r['heldout_accuracy'] for r in results)/len(results),.53)
        self.assertGreater(sum(r['heldout_accuracy'] for r in results)/len(results),.47)

    def test_reproducible_receipts(self):
        self.assertEqual(trial(42),trial(42))
        self.assertNotEqual(trial(42)[1],trial(43)[1])

    def test_holdout_size_does_not_affect_probe_selection(self):
        a,_=trial(5,n_test=128)
        b,_=trial(5,n_test=1024)
        self.assertEqual((a['matches'],a['selected']),(b['matches'],b['selected']))

    def test_missing_support_is_explicit(self):
        r,_=trial(11)
        self.assertEqual(r['support_coverage'],.5)
        self.assertEqual(r['assumption_violation'],'probes exclude x1=1')

if __name__=='__main__': unittest.main()
