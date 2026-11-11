"""Synthetic active-query control. Research only, not BEAN Core integration.

Fixed Boolean grammar and deterministic oracle. Disagreement sampling may inspect
candidate predictions but never the hidden target. Compare equal query budgets.
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

def run(seed, *, budget=2, strategy='disagreement'):
    if type(budget) is not int or not 0 <= budget <= len(INPUTS):
        raise ValueError('invalid query budget')
    if strategy not in ('disagreement','random'):
        raise ValueError('invalid query strategy')
    rng=random.Random(seed)
    truth=PROGRAMS[rng.randrange(len(PROGRAMS))]
    remaining=list(INPUTS)
    candidates=list(PROGRAMS)
    observations=[]
    for _ in range(budget):
        if strategy=='random':
            choice=rng.choice(remaining)
        else:
            rng.shuffle(remaining)
            choice=max(remaining,key=lambda x:min(
                sum(predict(p,x) for p in candidates),
                sum(not predict(p,x) for p in candidates)))
        remaining.remove(choice)
        y=predict(truth,choice)
        candidates=[p for p in candidates if predict(p,choice)==y]
        observations.append([list(choice),y])
    consensus=[{predict(p,x) for p in candidates} for x in INPUTS]
    correct=sum(len(v)==1 and next(iter(v))==predict(truth,x)
                for x,v in zip(INPUTS,consensus))
    return {'seed':seed,'budget':budget,'strategy':strategy,
            'truth':list(truth),'observations':observations,
            'remaining_hypotheses':len(candidates),
            'coverage':sum(len(v)==1 for v in consensus)/len(INPUTS),
            'correct_coverage':correct/len(INPUTS),
            'wrong_confident':sum(len(v)==1 and
                next(iter(v))!=predict(truth,x) for x,v in zip(INPUTS,consensus))}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,
                                   separators=(',',':')).encode()).hexdigest()

class ActiveCounterexampleControl(unittest.TestCase):
    def test_paired_fixed_budget(self):
        pairs=[(run(s),run(s,strategy='random')) for s in range(200)]
        active=sum(a['correct_coverage'] for a,b in pairs)/len(pairs)
        baseline=sum(b['correct_coverage'] for a,b in pairs)/len(pairs)
        self.assertGreaterEqual(active,baseline)
        self.assertTrue(all(a['wrong_confident']==b['wrong_confident']==0
                            for a,b in pairs))
        print('active %.4f random %.4f delta %.4f'%(active,baseline,active-baseline))

    def test_zero_budget_abstention_and_full_budget(self):
        self.assertLess(run(2,budget=0)['coverage'],1)
        for s in range(30):
            self.assertEqual(run(s,budget=4)['correct_coverage'],1)

    def test_restart_and_tamper(self):
        value=run(17)
        recovered=json.loads(json.dumps(value))
        self.assertEqual(digest(value),digest(recovered))
        recovered['observations'][0][1]^=1
        self.assertNotEqual(digest(value),digest(recovered))

    def test_invalid_design(self):
        for opts in ({'budget':-1},{'budget':5},{'budget':True},
                     {'strategy':'oracle'}):
            with self.assertRaises(ValueError):run(1,**opts)

if __name__=='__main__':unittest.main()
