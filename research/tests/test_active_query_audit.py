"""Synthetic negative control: independent audit probes for misspecified active learners.

All results are research-only. The hypothesis class excludes both target rules.
An audit probe is a uniform random unqueried input on the final query, not a
guarantee of detecting misspecification. No BEAN Core integration.
"""
import hashlib
import json
import random
import unittest

INPUTS = tuple((a,b) for a in (0,1) for b in (0,1))
OPS = (lambda a,b:a^b, lambda a,b:a&b, lambda a,b:a|b)
PROGRAMS = tuple((i,j) for i in range(3) for j in range(3))

def predict(p,x):
    a,b=x
    return OPS[p[1]](OPS[p[0]](a,b),a)

def oracle(x,kind):
    a,b=x
    return 1-(a&b) if kind=='nand' else 1-a

def trial(seed,kind='nand',strategy='disagreement',budget=3):
    if kind not in ('nand','not_a') or strategy not in ('disagreement','audit','random') or type(budget) is not int or not 0<=budget<=4:
        raise ValueError('invalid design')
    rng=random.Random(seed)
    remaining=list(INPUTS)
    candidates=list(PROGRAMS)
    observations=[]
    for step in range(budget):
        if not candidates:
            break
        if strategy=='random' or (strategy=='audit' and step==budget-1):
            x=rng.choice(remaining)
        else:
            rng.shuffle(remaining)
            x=max(remaining,key=lambda x:min(sum(predict(p,x) for p in candidates),sum(not predict(p,x) for p in candidates)))
        remaining.remove(x)
        y=oracle(x,kind)
        observations.append([list(x),y])
        candidates=[p for p in candidates if predict(p,x)==y]
    guesses=[{predict(p,x) for p in candidates} for x in remaining] if candidates else []
    wrong=sum(len(g)==1 and next(iter(g))!=oracle(x,kind) for g,x in zip(guesses,remaining))
    return {'seed':seed,'kind':kind,'strategy':strategy,'budget':budget,'observations':observations,
            'contradiction':not bool(candidates),'wrong_unqueried':wrong,
            'confident_unqueried':sum(len(g)==1 for g in guesses)}

def sha(receipt):
    return hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class AuditProbe(unittest.TestCase):
    def test_misspecification(self):
        for kind in ('nand','not_a'):
            self.assertFalse(any(all(predict(p,x)==oracle(x,kind) for x in INPUTS) for p in PROGRAMS))
    def test_paired_controls(self):
        runs={(k,s):[trial(i,k,s) for i in range(200)] for k in ('nand','not_a') for s in ('disagreement','audit','random')}
        for kind in ('nand','not_a'):
            for strategy in ('disagreement','audit','random'):
                data=runs[kind,strategy]
                print(kind,strategy,'contradictions',sum(r['contradiction'] for r in data),'wrong',sum(r['wrong_unqueried'] for r in data))
                self.assertTrue(all(r['wrong_unqueried']==0 for r in data if r['contradiction']))
        self.assertTrue(any(r['wrong_unqueried'] for data in runs.values() for r in data))
    def test_full_budget(self):
        for kind in ('nand','not_a'):
            for strategy in ('disagreement','audit','random'):
                for seed in range(30):
                    self.assertTrue(trial(seed,kind,strategy,4)['contradiction'])
    def test_receipt_restart_and_tamper(self):
        r=trial(9,strategy='audit')
        restored=json.loads(json.dumps(r))
        self.assertEqual(sha(r),sha(restored))
        restored['observations'][0][1]^=1
        self.assertNotEqual(sha(r),sha(restored))
    def test_invalid(self):
        for kwargs in ({'kind':'unknown'},{'strategy':'other'},{'budget':True},{'budget':5}):
            with self.assertRaises(ValueError):trial(0,**kwargs)

if __name__=='__main__':unittest.main()
