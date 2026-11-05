"""Synthetic negative control: randomized audits under selective feedback.

Research only, not a BEAN Core integration. Predictions precede outcomes.
Audit labels are sampled independently of correctness, unlike routine labels.
"""
import hashlib
import json
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path


def trial(seed, shifted, n=4000, audit_rate=0.12):
    rng = random.Random(seed)
    observations = []
    for i in range(n):
        x = rng.randrange(2)
        true_y = x ^ int(shifted and i >= n // 2)
        prediction = x  # frozen source rule; no target labels used
        error = int(prediction != true_y)
        routine = rng.random() < (0.8 if not error else 0.02)
        audit = rng.random() < audit_rate  # independently randomized
        observations.append((i, prediction, true_y, error, int(routine), int(audit)))
    return observations


def metrics(rows):
    routine = [r for r in rows if r[4]]
    audits = [r for r in rows if r[5]]
    return {
        "actual": sum(r[3] for r in rows) / len(rows),
        "routine": sum(r[3] for r in routine) / len(routine) if routine else None,
        "audit": sum(r[3] for r in audits) / len(audits) if audits else None,
        "audited": len(audits),
        "n": len(rows),
    }


def receipt(rows):
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


class RandomAuditCalibrationTests(unittest.TestCase):
    def test_shift_exposes_missing_not_at_random_bias(self):
        for seed in range(20):
            m = metrics(trial(seed, True))
            self.assertEqual(m["actual"], 0.5)
            self.assertLess(m["routine"], 0.05)
            self.assertLess(abs(m["audit"] - m["actual"]), 0.09)
            self.assertGreater(m["audited"], 350)

    def test_stationary_control(self):
        for seed in range(20, 40):
            m = metrics(trial(seed, False))
            self.assertEqual(m["actual"], 0)
            self.assertEqual(m["routine"], 0)
            self.assertEqual(m["audit"], 0)

    def test_zero_audit_is_unidentifiable(self):
        m = metrics(trial(41, True, audit_rate=0))
        self.assertIsNone(m["audit"])
        self.assertLess(m["routine"], 0.05)
        self.assertEqual(m["actual"], 0.5)

    def test_deterministic_receipt_and_restart(self):
        rows = trial(42, True)
        digest = receipt(rows)
        self.assertEqual(digest, receipt(trial(42, True)))
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "synthetic.sqlite"
            con = sqlite3.connect(db)
            try:
                con.execute("CREATE TABLE audit (step INTEGER PRIMARY KEY, prediction INTEGER, truth INTEGER, error INTEGER, routine INTEGER, audited INTEGER)")
                con.executemany("INSERT INTO audit VALUES (?,?,?,?,?,?)", rows)
                con.commit()
            finally:
                con.close()
            con = sqlite3.connect(db)
            try:
                restored = con.execute("SELECT * FROM audit ORDER BY step").fetchall()
            finally:
                con.close()
            self.assertEqual(digest, receipt(restored))
            self.assertEqual(metrics(rows), metrics(restored))

    def test_fixed_budget_and_no_future_label_dependency(self):
        rows = trial(43, True)
        self.assertEqual(len(rows), 4000)
        stationary = trial(43, False)
        self.assertEqual([r[1] for r in rows], [r[1] for r in stationary])
        self.assertEqual([r[5] for r in rows], [r[5] for r in stationary])


if __name__ == "__main__":
    unittest.main()
