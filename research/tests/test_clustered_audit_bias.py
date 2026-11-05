"""Synthetic negative control: clustered audits invalidate naive IID intervals.

Research only. No BEAN inference, private data or runtime policy changes.
"""
import hashlib
import json
import math
import random
import unittest


def wilson(errors, n, z=1.959963984540054):
    if n == 0:
        return 0.0, 1.0
    p = errors / n
    d = 1 + z*z/n
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    c = (p + z*z/(2*n))/d
    return max(0.0, c-h), min(1.0, c+h)


def evaluate(seed, clusters=40, size=20, rate=.25):
    """Each cluster has one independent error bit shared by all its records."""
    rng = random.Random(seed)
    bits = [int(rng.random() < .5) for _ in range(clusters)]
    selected = [i for i in range(clusters) if rng.random() < rate]
    errors = sum(bits[i] for i in selected)
    k = len(selected)
    return {"seed": seed, "selected": selected, "bits": bits,
            "naive": wilson(errors * size, k * size),
            "cluster": wilson(errors, k), "truth": .5,
            "audit_records": k * size, "independent_units": k}


class ClusteredAuditControls(unittest.TestCase):
    def test_heldout_coverage_penalty_from_pseudoreplication(self):
        cases = [evaluate(s) for s in range(1000, 1400)]
        naive = sum(x["naive"][0] <= .5 <= x["naive"][1] for x in cases)
        cluster = sum(x["cluster"][0] <= .5 <= x["cluster"][1] for x in cases)
        self.assertGreater(cluster, naive + 100)
        self.assertGreater(cluster, 250)

    def test_zero_audit_retains_full_uncertainty(self):
        x = evaluate(7, rate=0)
        self.assertEqual(x["naive"], (0, 1))
        self.assertEqual(x["cluster"], (0, 1))

    def test_cluster_uncertainty_is_wider(self):
        x = evaluate(10)
        self.assertGreater(x["independent_units"], 0)
        self.assertLessEqual(x["naive"][1] - x["naive"][0],
                             x["cluster"][1] - x["cluster"][0])

    def test_deterministic_receipt_and_no_future_feedback(self):
        x = evaluate(2026)
        y = evaluate(2026)
        self.assertEqual(x, y)
        receipt = hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()
        self.assertEqual(receipt, hashlib.sha256(json.dumps(y, sort_keys=True).encode()).hexdigest())
        rng = random.Random(2026)
        _ = [rng.random() for _ in range(40)]
        self.assertEqual(x["selected"], [i for i in range(40) if rng.random() < .25])


if __name__ == "__main__":
    unittest.main()
