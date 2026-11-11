"""Synthetic audit negative control: repeated outcomes are not independent evidence.

One latent Bernoulli error per cluster is copied across ten observations. A
naive observation-level interval treats copies as new information; a cluster
interval treats each independent latent draw as one unit. This is a research
control, not a production BEAN estimator or proof of calibrated confidence.
"""
import hashlib
import json
import math
import random
import unittest


def trial(seed, clusters=24, copies=10, alpha_z=1.96):
    if not isinstance(clusters, int) or clusters < 2 or not isinstance(copies, int) or copies < 1:
        raise ValueError("invalid cluster design")
    rng = random.Random(seed)
    latent = [int(rng.random() < 0.5) for _ in range(clusters)]
    observations = [v for v in latent for _ in range(copies)]
    mean = sum(observations) / len(observations)
    # Known null variance p(1-p) with p=.5, so this isolates dependence.
    naive_radius = alpha_z * math.sqrt(0.25 / len(observations))
    cluster_radius = alpha_z * math.sqrt(0.25 / clusters)
    result = {"seed": seed, "clusters": clusters, "copies": copies,
              "cluster_outcomes": latent, "n_observations": len(observations),
              "estimate": mean, "naive_radius": naive_radius,
              "cluster_radius": cluster_radius,
              "naive_misses_null": abs(mean - 0.5) > naive_radius,
              "cluster_misses_null": abs(mean - 0.5) > cluster_radius}
    result["sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result


class ClusterDependenceAudit(unittest.TestCase):
    def test_pseudoreplication_false_certainty(self):
        rows = [trial(seed) for seed in range(1000)]
        naive = sum(row["naive_misses_null"] for row in rows)
        cluster = sum(row["cluster_misses_null"] for row in rows)
        self.assertGreater(naive, 300)
        self.assertLess(cluster, 100)
        self.assertGreater(naive, cluster * 4)

    def test_single_copy_control(self):
        for seed in range(100):
            row = trial(seed, copies=1)
            self.assertEqual(row["naive_radius"], row["cluster_radius"])
            self.assertEqual(row["naive_misses_null"], row["cluster_misses_null"])

    def test_more_copies_do_not_add_independent_evidence(self):
        for seed in range(40):
            a, b = trial(seed, copies=1), trial(seed, copies=50)
            self.assertEqual(a["estimate"], b["estimate"])
            self.assertEqual(a["cluster_radius"], b["cluster_radius"])
            self.assertLess(b["naive_radius"], a["naive_radius"])

    def test_restart_and_receipt_tampering(self):
        original = trial(123)
        restored = json.loads(json.dumps(original))
        self.assertEqual(original, restored)
        digest = restored.pop("sha256")
        self.assertEqual(digest, hashlib.sha256(json.dumps(restored, sort_keys=True).encode()).hexdigest())
        restored["cluster_outcomes"][0] ^= 1
        self.assertNotEqual(digest, hashlib.sha256(json.dumps(restored, sort_keys=True).encode()).hexdigest())

    def test_invalid_design(self):
        for clusters, copies in [(1, 10), (24, 0), (2.5, 10), (24, 1.5)]:
            with self.assertRaises(ValueError):
                trial(0, clusters, copies)


if __name__ == "__main__":
    unittest.main()
