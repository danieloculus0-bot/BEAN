"""Synthetic negative control: hypothesis-class expansion after counterexamples.

No BEAN runtime integration or real-world oracle. Four Boolean input rows;
16 possible rules, four initial candidate rules. Equal three-query budgets.
"""
import hashlib
import json
import random
import unittest

BASE = ((0, 0, 1, 1), (0, 1, 0, 1), (0, 0, 0, 1), (0, 1, 1, 1))
RULES = tuple(tuple((mask >> i) & 1 for i in range(4)) for mask in range(16))


def infer(observed, expand=False):
    candidates = [r for r in BASE if all(r[i] == y for i, y in observed.items())]
    if candidates:
        return candidates, "base"
    if not expand:
        return [], "contradiction"
    return [r for r in RULES if all(r[i] == y for i, y in observed.items())], "expanded"


def predict(candidates, index):
    labels = {r[index] for r in candidates}
    return next(iter(labels)) if len(labels) == 1 else None


def trial(seed, rule, expand=False):
    order = list(range(4))
    random.Random(seed).shuffle(order)
    observed = {}
    steps = []
    for index in order[:3]:
        observed[index] = rule[index]
        candidates, status = infer(observed, expand)
        unseen = [j for j in range(4) if j not in observed]
        predictions = [predict(candidates, j) for j in unseen]
        steps.append({
            "query": index, "status": status,
            "correct": sum(p == rule[j] for p, j in zip(predictions, unseen) if p is not None),
            "wrong": sum(p != rule[j] for p, j in zip(predictions, unseen) if p is not None),
            "abstained": sum(p is None for p in predictions),
        })
    return steps


def evaluate():
    records = [
        {"seed": seed, "rule": rule_id, "expand": expand,
         "steps": trial(seed, rule, expand)}
        for seed in range(100)
        for rule_id, rule in enumerate(RULES)
        for expand in (False, True)
    ]
    payload = {"protocol": "counterexample-repair-negative-v1", "records": records}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return {"payload": payload, "sha256": hashlib.sha256(encoded.encode()).hexdigest()}


class TestCounterexampleRepair(unittest.TestCase):
    def test_full_counterexample_reveals_misspecification(self):
        xor = (0, 1, 1, 0)
        observed = dict(enumerate(xor))
        self.assertEqual(infer(observed)[1], "contradiction")
        self.assertEqual(infer(observed, True), ([xor], "expanded"))

    def test_partial_expansion_abstains(self):
        candidates, status = infer({0: 1, 1: 0, 2: 0}, True)
        self.assertEqual(status, "expanded")
        self.assertIsNone(predict(candidates, 3))

    def test_expansion_does_not_create_false_certainty(self):
        for rule in RULES:
            for seed in range(100):
                for step in trial(seed, rule, True):
                    if step["status"] == "expanded":
                        self.assertEqual(step["wrong"], 0)

    def test_paired_negative_result(self):
        receipt = evaluate()
        totals = {}
        for expand in (False, True):
            steps = [
                step for row in receipt["payload"]["records"]
                if row["expand"] == expand for step in row["steps"]
            ]
            totals[expand] = tuple(sum(step[key] for step in steps)
                                   for key in ("correct", "wrong", "abstained"))
        # Expanded version space never changes confident predictions in this
        # particular protocol: it only replaces contradiction with abstention.
        self.assertEqual(totals[False], totals[True])
        self.assertEqual(totals[True], (1576, 1576, 6448))

    def test_json_restart_and_tamper(self):
        receipt = json.loads(json.dumps(evaluate()))
        raw = json.dumps(receipt["payload"], sort_keys=True, separators=(",", ":"))
        self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), receipt["sha256"])
        receipt["payload"]["records"][0]["steps"][0]["query"] = 99
        tampered = json.dumps(receipt["payload"], sort_keys=True, separators=(",", ":"))
        self.assertNotEqual(hashlib.sha256(tampered.encode()).hexdigest(), receipt["sha256"])


if __name__ == "__main__":
    unittest.main()
