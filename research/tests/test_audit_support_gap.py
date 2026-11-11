"""Synthetic audit support gap: missing outcome strata invalidate population claims.

Research only. Random audit labels are assumed independent of outcomes conditional
on strata. No production BEAN integration or AGI claim.
"""
import hashlib
import json
import random
import unittest


def trial(seed, audit_budget=120, target_mix=(0.5, 0.5), blocked=False):
    """Compare selective routine feedback with an independent audit.

    The second stratum has 90% error, the first 10%; routine feedback
    preferentially reveals correct decisions. Audit sample is uniform from
    the target population unless blocked, when stratum 1 is inaccessible.
    """
    if audit_budget < 1 or not 0 < target_mix[0] < 1 or abs(sum(target_mix)-1) > 1e-9:
        raise ValueError('invalid budget or population mix')
    rng = random.Random(seed)
    population = []
    for stratum, n in enumerate((int(2000 * target_mix[0]), 2000-int(2000 * target_mix[0]))):
        for _ in range(n):
            err = int(rng.random() < (0.1 if stratum == 0 else 0.9))
            observed = rng.random() < (0.8 if not err else 0.04)
            population.append((stratum, err, observed))
    routine = [r[1] for r in population if r[2]]
    eligible = [(i, r) for i, r in enumerate(population) if not blocked or r[0] == 0]
    chosen = rng.sample(eligible, min(audit_budget, len(eligible)))
    audited = [r for _, r in chosen]
    counts = [sum(r[0] == s for r in audited) for s in (0, 1)]
    estimate = None
    if all(counts):
        estimate = sum(target_mix[s] * sum(r[1] for r in audited if r[0] == s) / counts[s] for s in (0, 1))
    receipt = {'seed':seed, 'budget':audit_budget, 'blocked':blocked,
               'population_error':sum(r[1] for r in population)/len(population),
               'routine_error':sum(routine)/len(routine),
               'audit_error':estimate, 'audit_strata':counts,
               'audit_ids':[i for i, _ in chosen]}
    # Receipt hash is a checksum, not an authenticated anchor.
    receipt['sha256'] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    return receipt


class AuditSupportGap(unittest.TestCase):
    def test_independent_audit_beats_selective_feedback(self):
        rows = [trial(s) for s in range(40)]
        true = sum(x['population_error'] for x in rows)/len(rows)
        naive = sum(x['routine_error'] for x in rows)/len(rows)
        audited = sum(x['audit_error'] for x in rows)/len(rows)
        self.assertGreater(true-naive, 0.2)
        self.assertLess(abs(true-audited), 0.04)

    def test_missing_stratum_abstains(self):
        for seed in range(20):
            r = trial(seed, blocked=True)
            self.assertIsNone(r['audit_error'])
            self.assertEqual(r['audit_strata'][1], 0)

    def test_deterministic_restart_receipt(self):
        before = trial(87)
        after = json.loads(json.dumps(before))
        self.assertEqual(before, after)
        self.assertEqual(before, trial(87))
        digest = after.pop('sha256')
        self.assertEqual(digest, hashlib.sha256(json.dumps(after, sort_keys=True).encode()).hexdigest())

    def test_budget_validation(self):
        for budget in (0, -1):
            with self.assertRaises(ValueError):
                trial(1, audit_budget=budget)


if __name__ == '__main__':
    unittest.main()
