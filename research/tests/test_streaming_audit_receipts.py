"""Streaming synthetic audit interval with restartable, hash-checked receipts.

Research only. Assumes independent, randomly observed Bernoulli outcomes.
"""
import hashlib
import json
import math
import random
import unittest


class StreamingAudit:
    def __init__(self, alpha=0.05, n=0, errors=0):
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            raise ValueError("invalid count")
        if not isinstance(errors, int) or isinstance(errors, bool) or not 0 <= errors <= n:
            raise ValueError("invalid error count")
        if not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or not 0 < alpha < 1:
            raise ValueError("invalid alpha")
        self.alpha, self.n, self.errors = float(alpha), n, errors

    def observe(self, error):
        if type(error) is not int or error not in (0, 1):
            raise ValueError("audit outcome must be 0 or 1")
        self.n += 1
        self.errors += error

    def interval(self):
        if not self.n:
            return (0.0, 1.0)
        r = math.sqrt(math.log(2*self.n*(self.n+1)/self.alpha)/(2*self.n))
        p = self.errors/self.n
        return max(0.0, p-r), min(1.0, p+r)

    def receipt(self):
        state = {"schema": 1, "alpha": self.alpha, "n": self.n,
                 "errors": self.errors, "assumptions": "iid_bernoulli_random_audit"}
        digest = hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {"state": state, "sha256": digest}

    @classmethod
    def restore(cls, receipt):
        state = receipt["state"]
        digest = hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if digest != receipt["sha256"] or state.get("schema") != 1 or state.get("assumptions") != "iid_bernoulli_random_audit":
            raise ValueError("invalid receipt")
        return cls(alpha=state["alpha"], n=state["n"], errors=state["errors"])


class StreamingAuditTests(unittest.TestCase):
    def test_paired_batch_and_restart(self):
        for seed in (7, 11, 37, 101):
            rng = random.Random(seed)
            outcomes = [int(rng.random() < .2) for _ in range(1000)]
            stream = StreamingAudit()
            for i, outcome in enumerate(outcomes):
                if i == 499:
                    stream = StreamingAudit.restore(json.loads(json.dumps(stream.receipt())))
                stream.observe(outcome)
                if i in (0, 9, 99, 499, 999):
                    n = i + 1
                    radius = math.sqrt(math.log(2*n*(n+1)/.05)/(2*n))
                    p = sum(outcomes[:n])/n
                    self.assertEqual(stream.interval(), (max(0.0, p-radius), min(1.0, p+radius)))
            self.assertEqual(stream.receipt(), StreamingAudit.restore(stream.receipt()).receipt())

    def test_reject_tampering(self):
        receipt = StreamingAudit().receipt()
        receipt["state"]["errors"] = 1
        with self.assertRaises(ValueError):
            StreamingAudit.restore(receipt)

    def test_invalid_inputs_do_not_mutate(self):
        stream = StreamingAudit()
        for invalid in (-1, 2, True, .5, None):
            with self.assertRaises(ValueError):
                stream.observe(invalid)
        self.assertEqual(stream.n, 0)
        for n, errors in ((-1, 0), (1, 2), (True, 0)):
            with self.assertRaises(ValueError):
                StreamingAudit(n=n, errors=errors)

    def test_negative_control_correlated_labels(self):
        stream = StreamingAudit()
        for _ in range(200):
            stream.observe(1)
        self.assertGreater(stream.interval()[0], .5)
        # Duplicates of one latent observation are not 200 independent audits.
        self.assertFalse(stream.interval()[0] <= .2 <= stream.interval()[1])


if __name__ == "__main__":
    unittest.main()
