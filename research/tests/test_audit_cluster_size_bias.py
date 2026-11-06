"""Synthetic negative control: informative cluster size distorts event-level audits.

Research only. No BEAN Core integration, inference or AGI claim.
"""
import hashlib
import json
import random
import unittest


def experiment(seed, clusters=300, sample=60):
    """Compare equal-cluster sampling against event-weighted population risk.

    Large clusters have more observations and greater error probability. Sampling
    clusters uniformly then averaging their errors estimates *cluster* risk,
    not *event* risk. The size-weighted estimate targets event risk.
    """
    if clusters < 20 or not 2 <= sample <= clusters:
        raise ValueError('invalid audit budget')
    rng = random.Random(seed)
    population = []
    for i in range(clusters):
        large = i % 3 == 0
        size = 30 if large else 2
        # One shared error outcome per cluster, preserving correlation.
        error = int(rng.random() < (.8 if large else .1))
        population.append((size, error))
    audit = rng.sample(population, sample)
    cluster_est = sum(error for _, error in audit) / sample
    weighted_est = sum(size * error for size, error in audit) / sum(size for size, _ in audit)
    truth = sum(size * error for size, error in population) / sum(size for size, _ in population)
    receipt = {'seed': seed, 'clusters': clusters, 'sample': sample,
               'truth': truth, 'cluster_est': cluster_est,
               'weighted_est': weighted_est, 'audit': [list(item) for item in audit]}
    digest = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'receipt': receipt, 'sha256': digest}


class ClusterSizeBiasTests(unittest.TestCase):
    def test_paired_seeded_evaluation(self):
        trials = [experiment(s)['receipt'] for s in range(100)]
        naive = sum(abs(r['cluster_est'] - r['truth']) for r in trials) / len(trials)
        weighted = sum(abs(r['weighted_est'] - r['truth']) for r in trials) / len(trials)
        self.assertGreater(naive, .35)
        self.assertLess(weighted, naive * .5)

    def test_full_population_recovers_event_risk(self):
        r = experiment(13, 300, 300)['receipt']
        self.assertAlmostEqual(r['weighted_est'], r['truth'])
        self.assertNotAlmostEqual(r['cluster_est'], r['truth'], places=2)

    def test_restart_and_tamper_evidence(self):
        a = experiment(17)
        self.assertEqual(a, json.loads(json.dumps(a)))
        self.assertEqual(a, experiment(17))
        self.assertNotEqual(a['sha256'], experiment(18)['sha256'])
        altered = json.loads(json.dumps(a))
        altered['receipt']['audit'][0][1] ^= 1
        digest = hashlib.sha256(json.dumps(altered['receipt'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertNotEqual(digest, a['sha256'])

    def test_invalid_budgets(self):
        for clusters, sample in [(19, 10), (300, 1), (300, 301)]:
            with self.assertRaises(ValueError):
                experiment(1, clusters, sample)


if __name__ == '__main__':
    unittest.main()
