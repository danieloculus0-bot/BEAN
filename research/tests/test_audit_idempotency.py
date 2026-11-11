"""Synthetic negative control: replayed audit receipts are not new evidence.

Research-only, not wired into BEAN Core. Identifiers are scoped by producer;
identical payload hashes alone cannot establish independent observations.
"""
import hashlib
import json
import random
import unittest


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class AuditAccumulator:
    """Reference replay reducer, not a new BEAN memory backend."""

    def __init__(self, state=None):
        self.receipts = {} if state is None else dict(state["receipts"])
        self._validate()

    def _validate(self):
        for key, receipt in self.receipts.items():
            if key != receipt["producer"] + ":" + receipt["id"]:
                raise ValueError("receipt identity mismatch")
            if receipt["error"] not in (0, 1) or type(receipt["error"]) is not int:
                raise ValueError("invalid outcome")

    def add(self, producer, identifier, error):
        if not isinstance(producer, str) or not producer or not isinstance(identifier, str) or not identifier:
            raise ValueError("missing stable identity")
        if type(error) is not int or error not in (0, 1):
            raise ValueError("outcome must be binary")
        key = producer + ":" + identifier
        receipt = {"producer": producer, "id": identifier, "error": error}
        if key in self.receipts:
            if self.receipts[key] != receipt:
                raise ValueError("conflicting replay; retain both source events for investigation")
            return False
        self.receipts[key] = receipt
        return True

    def snapshot(self):
        ordered = {k: self.receipts[k] for k in sorted(self.receipts)}
        return {"receipts": ordered, "sha256": digest(ordered)}

    @classmethod
    def restore(cls, snapshot):
        if digest(snapshot["receipts"]) != snapshot["sha256"]:
            raise ValueError("modified snapshot")
        return cls(snapshot)

    def error_rate(self):
        n = len(self.receipts)
        return sum(r["error"] for r in self.receipts.values()) / n if n else None


class AuditIdempotencyTests(unittest.TestCase):
    def test_duplicate_replay_does_not_inflate_denominator(self):
        a = AuditAccumulator()
        for i in range(100):
            a.add("sim", str(i), int(i % 4 == 0))
        original = a.snapshot()
        for i in range(100):
            self.assertFalse(a.add("sim", str(i), int(i % 4 == 0)))
        self.assertEqual(a.error_rate(), 0.25)
        self.assertEqual(a.snapshot(), original)

    def test_conflict_rejected_not_silently_overwritten(self):
        a = AuditAccumulator()
        a.add("sim", "7", 1)
        with self.assertRaises(ValueError):
            a.add("sim", "7", 0)
        self.assertEqual(a.error_rate(), 1)

    def test_restart_and_order_independent_replay(self):
        rng = random.Random(2317)
        events = [("sim", str(i), rng.randrange(2)) for i in range(200)]
        a = AuditAccumulator()
        for event in events:
            a.add(*event)
        snapshot = json.loads(canonical(a.snapshot()))
        b = AuditAccumulator.restore(snapshot)
        rng.shuffle(events)
        for event in events:
            self.assertFalse(b.add(*event))
        self.assertEqual(b.snapshot(), snapshot)

    def test_tamper_and_invalid_replay(self):
        a = AuditAccumulator()
        a.add("sim", "1", 0)
        snap = a.snapshot()
        snap["receipts"]["sim:1"]["error"] = 1
        with self.assertRaises(ValueError):
            AuditAccumulator.restore(snap)
        with self.assertRaises(ValueError):
            a.add("sim", "2", True)

    def test_identical_payloads_from_distinct_ids_are_not_deduplicated(self):
        a = AuditAccumulator()
        a.add("sim", "1", 1)
        a.add("sim", "2", 1)
        self.assertEqual(len(a.receipts), 2)
        # Distinct IDs are not proof of statistical independence: this test
        # deliberately makes no confidence-interval claim.


if __name__ == "__main__":
    unittest.main()
