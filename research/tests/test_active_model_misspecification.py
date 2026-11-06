"""Research-only negative control: active querying with a misspecified hypothesis class.

A unanimous surviving version space can be confidently wrong. An empty version
space is a contradiction, not vacuous consensus. Synthetic Boolean oracle only.
"""
import hashlib
import json
import random
import unittest

OPS = (lambda a,b:a^b, lambda a,b:a&b, lambda a,b:a|b)
PROGRAMS = tuple((a,b) for a in range(3) for b in range(3))
INPUTS = tuple((a,b) for a in range(2) for b in range(2))

def predict(program, pair):
    a,b=pair
    return OPS[program[1]](OPS[program[0]](a,b),a)

def truth(pair, kind):
    a,b=pair
    return (1-(a&b)) if kind=='nand' else (1-a)

def run(seed, *, kind='nand', budget=2, strategy='disagreement'):
    if kind not in ('nand','not_a') or strategy not in ('disagreement','random') or type(budget) is not int or not 0<=budget<=4:
        raise ValueError('invalid design')
    rng=random.Random(seed)
    remaining=list(INPUTS)
    candidates=list(PROGRAMS)
    observations=[]
    for _ in range(budget):
        if strategy=='random':
            chosen=rng.choice(remaining)
        else:
            rng.shuffle(remaining)
            chosen=max(remaining,key=lambda x:min(sum(predict(p,x) for p in candidates),sum(not predict(p,x) for p in candidates)))
        remaining.remove(chosen)
        y=truth(chosen,kind)
        observations.append([list(chosen),y])
        candidates=[p for p in candidates if predict(p,chosen)==y]
        if not candidates:
            break
    unqueried=[x for x in INPUTS if x not in [tuple(o[0]) for o in observations]]
    consensus=[{predict(p,x) for p in candidates} for x in unqueried]
    confident=[next(iter(v)) if len(v)==1 else None for v in consensus] if candidates else [None]*len(unqueried)
    wrong=sum(v is not None and v!=truth(x,kind) for v,x in zip(confident,unqueried))
    return {'seed':seed,'kind':kind,'strategy':strategy,'budget':budget,
            'observations':observations,'remaining':len(candidates),
            'contradiction':not bool(candidates),'unqueried':len(unqueried),
            'confident_unqueried':sum(v is not None for v in confident),
            'wrong_unqueried':wrong}

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class MisspecificationControl(unittest.TestCase):
    def test_truth_not_representable(self):
        for kind in ('nand','not_a'):
            self.assertFalse(any(all(predict(p,x)==truth(x,kind) for x in INPUTS) for p in PROGRAMS))

    def test_full_budget_detects_contradiction(self):
        for kind in ('nand','not_a'):
            for seed in range(40):
                for strategy in ('disagreement','random'):
                    result=run(seed,kind=kind,budget=4,strategy=strategy)
                    self.assertTrue(result['contradiction'])
                    self.assertEqual(result['wrong_unqueried'],0)

    def test_paired_short_budget_and_negative_evidence(self):
        pairs=[(run(s,kind=k),run(s,kind=k,strategy='random')) for k in ('nand','not_a') for s in range(200)]
        self.assertTrue(any(x['wrong_unqueried']>0 for pair in pairs for x in pair))
        self.assertTrue(any(x['contradiction'] for pair in pairs for x in pair))
        self.assertTrue(all(x['wrong_unqueried']==0 if x['contradiction'] else True for pair in pairs for x in pair))
        for i in (0,1):
            vals=[p[i] for p in pairs]
            print(('active','random')[i], 'contradictions',sum(v['contradiction'] for v in vals),
                  'wrong unqueried',sum(v['wrong_unqueried'] for v in vals),
                  'confident unqueried',sum(v['confident_unqueried'] for v in vals))

    def test_restart_receipt_and_tamper(self):
        r=run(11)
        recovered=json.loads(json.dumps(r))
        self.assertEqual(digest(r),digest(recovered))
        recovered['observations'][0][1]^=1
        self.assertNotEqual(digest(r),digest(recovered))

    def test_invalid_design(self):
        for kw in ({'kind':'magic'},{'strategy':'oracle'},{'budget':True},{'budget':-1},{'budget':5}):
            with self.assertRaises(ValueError):run(1,**kw)

if __name__=='__main__':unittest.main()
