"""Synthetic stratified audit of transfer claims under covariate shift.

Research only. Independent audit inclusion within each stratum is required;
source similarity is not proof of transfer. No BEAN runtime changes.
"""
import hashlib
import json
import random
import unittest


def stratified_estimate(strata):
    if not all(strata.get(s) for s in ('A', 'B')):
        return None
    return 0.2 * sum(strata['A']) / len(strata['A']) + 0.8 * sum(strata['B']) / len(strata['B'])


def evaluate(seed, *, n=4000, shifted=True, audit_rate=0.2):
    if not 0 < audit_rate <= 1 or n < 100 or n % 10:
        raise ValueError('invalid budget')
    rng = random.Random(seed)
    rows = []
    # Target population is 80% rare-in-source stratum B, where transfer fails.
    for i in range(n):
        stratum = 'B' if i % 5 else 'A'
        error = int(shifted and stratum == 'B')
        # Convenience feedback overrepresents A; randomized audit does not.
        routine = rng.random() < (0.95 if stratum == 'A' else 0.03)
        audit = rng.random() < audit_rate
        rows.append((i, stratum, error, int(routine), int(audit)))
    def mean(rs):
        return sum(x[2] for x in rs) / len(rs) if rs else None
    routine_rows = [r for r in rows if r[3]]
    audit_rows = [r for r in rows if r[4]]
    # Fixed population proportions are known from prelabel metadata.
    strata = {s: [r for r in audit_rows if r[1] == s] for s in ('A', 'B')}
    stratified = stratified_estimate({s: [r[2] for r in rs] for s, rs in strata.items()})
    return {'actual': mean(rows), 'routine': mean(routine_rows),
            'audit': mean(audit_rows), 'stratified': stratified,
            'audit_n': len(audit_rows),
            'audit_strata': {s: len(v) for s, v in strata.items()},
            'sha256': hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()}


class StratifiedAuditTests(unittest.TestCase):
    def test_shifted_population_and_baseline(self):
        outcomes = [evaluate(s) for s in range(50)]
        self.assertTrue(all(x['actual'] == 0.8 for x in outcomes))
        self.assertLess(sum(x['routine'] for x in outcomes) / 50, 0.15)
        self.assertLess(sum(abs(x['audit'] - 0.8) for x in outcomes) / 50, 0.04)
        self.assertTrue(all(abs(x['stratified'] - 0.8) < 1e-12 for x in outcomes))

    def test_stationary_control(self):
        self.assertTrue(all(evaluate(s, shifted=False)['stratified'] == 0 for s in range(20)))

    def test_restart_determinism_and_hash(self):
        a = evaluate(123)
        self.assertEqual(a, json.loads(json.dumps(a)))
        self.assertEqual(a, evaluate(123))
        self.assertNotEqual(a['sha256'], evaluate(124)['sha256'])

    def test_missing_stratum_cannot_be_silently_imputed(self):
        self.assertIsNone(stratified_estimate({'A': [0] * 12, 'B': []}))
        self.assertIsNone(stratified_estimate({'A': [], 'B': [1] * 12}))

    def test_invalid_budget(self):
        for rate in (0, -0.1, 1.1):
            with self.assertRaises(ValueError):
                evaluate(1, audit_rate=rate)


if __name__ == '__main__':
    unittest.main()
