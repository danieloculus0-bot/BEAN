"""Exhaustive synthetic identifiability limit for active hypothesis audits.

Even a perfectly consistent partial transcript cannot certify an arbitrary
four-input Boolean rule. Some alternatives are in-class, some out-of-class.
Research-only; no BEAN Core wiring or general-intelligence claim.
"""
import hashlib
import itertools
import json
import unittest

INPUTS = tuple(itertools.product((0, 1), repeat=2))
OPS = (lambda a,b:a^b, lambda a,b:a&b, lambda a,b:a|b)
PROGRAMS = tuple(itertools.product(range(3), repeat=2))

def predict(program, x):
    a,b=x
    return OPS[program[1]](OPS[program[0]](a,b),a)

def signatures():
    return {tuple(predict(p,x) for x in INPUTS) for p in PROGRAMS}

def indistinguishable_counterexamples(budget):
    if type(budget) is not int or not 0 <= budget <= len(INPUTS):
        raise ValueError('budget must be an integer in [0,4]')
    known=signatures()
    all_rules=set(itertools.product((0,1),repeat=len(INPUTS)))
    results=[]
    for candidate in sorted(known):
        for observed in itertools.combinations(range(len(INPUTS)),budget):
            alternatives=[rule for rule in all_rules-known
                          if all(rule[i]==candidate[i] for i in observed)]
            results.append({'candidate':candidate,'queried':observed,
                            'undetected_out_of_class':len(alternatives),
                            'undetected_alternatives':2**(len(INPUTS)-budget)-1})
    return results

def receipt(budget):
    cases=indistinguishable_counterexamples(budget)
    return {'schema':'synthetic-identifiability-v1','budget':budget,
            'candidate_rules':len(signatures()),'all_boolean_rules':16,
            'query_subsets':len(cases),
            'undetectable_pairs':sum(c['undetected_out_of_class'] for c in cases),
            'cases':cases}

def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class IdentifiabilityTests(unittest.TestCase):
    def test_exhaustive_hypothesis_class(self):
        self.assertEqual(len(signatures()),len({tuple(predict(p,x) for x in INPUTS) for p in PROGRAMS}))
        self.assertLess(len(signatures()),16)

    def test_any_partial_query_has_counterexample(self):
        for budget in range(4):
            cases=indistinguishable_counterexamples(budget)
            self.assertTrue(cases)
            self.assertTrue(all(c['undetected_alternatives'] >= 1 for c in cases))
        self.assertTrue(all(c['undetected_alternatives']==0 for c in indistinguishable_counterexamples(4)))
        self.assertTrue(any(c['undetected_out_of_class']==0 for c in indistinguishable_counterexamples(3)))

    def test_adaptive_transcript_counterexample(self):
        # Any deterministic adaptive strategy stopping early has a different
        # rule yielding the same observed transcript, possibly still in-class.
        for candidate in signatures():
            for order in itertools.permutations(range(4)):
                for budget in range(4):
                    observed=order[:budget]
                    alternatives=[r for r in itertools.product((0,1),repeat=4)
                                  if r != candidate and all(r[i]==candidate[i] for i in observed)]
                    self.assertTrue(alternatives)

    def test_receipt_restart_and_tamper(self):
        original=receipt(3)
        restored=json.loads(json.dumps(original))
        self.assertEqual(digest(original),digest(restored))
        restored['cases'][0]['undetected_out_of_class']+=1
        self.assertNotEqual(digest(original),digest(restored))

    def test_invalid(self):
        for budget in (-1,5,True,2.0,'3'):
            with self.assertRaises(ValueError):receipt(budget)

if __name__=='__main__':
    unittest.main()
