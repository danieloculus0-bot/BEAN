"""Research-only compositional transfer probe; not integrated with BEAN Core.

A learner receives labeled source-domain examples of a two-step Boolean program.
Target uses unseen nuisance symbol names. Compare operator-structure transfer
against an exact-row memorizer and majority baseline. Target labels are held out.

Limitation: the symbolic operation grammar is provided in advance; this tests
fitting and reusing a tiny hypothesis class, not autonomous analogy discovery.
"""
import hashlib
import json
import random
import unittest

OPS = (lambda x, y: x ^ y, lambda x, y: x & y, lambda x, y: x | y)


def examples(seed, n, symbols):
    rng = random.Random(seed)
    return [(rng.choice(symbols), rng.choice(symbols),
             rng.randrange(2), rng.randrange(2)) for _ in range(n)]


def label(row, program):
    _, _, a, b = row
    return OPS[program[1]](OPS[program[0]](a, b), a)


def infer_program(source, labels):
    return [p for p in ((i, j) for i in range(3) for j in range(3))
            if all(label(r, p) == y for r, y in zip(source, labels))]


def evaluate(seed, *, train_n=32, test_n=96, program=(0, 1)):
    if train_n < 1 or test_n < 1 or any(i not in range(3) for i in program):
        raise ValueError("invalid budget or program")
    source = examples(seed, train_n, ("red", "blue"))
    target = examples(seed + 100000, test_n, ("circle", "square"))
    ys = [label(r, program) for r in source]
    candidates = infer_program(source, ys)
    lookup = {tuple(r): y for r, y in zip(source, ys)}
    majority = int(sum(ys) > len(ys) / 2)
    # Predict only when every source-consistent hypothesis agrees.
    transferred = [next(iter(predictions)) if len(predictions := {
        label(r, p) for p in candidates}) == 1 else None for r in target]
    memorized = [lookup.get(tuple(r), majority) for r in target]
    truth = [label(r, program) for r in target]
    return {
        "seed": seed, "train_n": train_n, "test_n": test_n,
        "program": list(program), "candidate_count": len(candidates),
        "coverage": sum(v is not None for v in transferred) / test_n,
        "transfer_accuracy": sum(a == b for a, b in zip(transferred, truth)
                                 if a is not None) / test_n,
        "memorizer_accuracy": sum(a == b for a, b in zip(memorized, truth)) / test_n,
        "majority_accuracy": sum(majority == b for b in truth) / test_n,
        "source_target_disjoint": set(r[0] for r in source).isdisjoint(
            r[0] for r in target),
    }


def digest(result):
    return hashlib.sha256(json.dumps(result, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


class CompositionalTransfer(unittest.TestCase):
    def test_held_out_transfer_vs_memorization(self):
        results = [evaluate(i) for i in range(100)]
        self.assertTrue(all(r["source_target_disjoint"] for r in results))
        self.assertGreater(sum(r["transfer_accuracy"] for r in results) / 100, 0.98)
        self.assertGreater(sum(r["transfer_accuracy"] - r["memorizer_accuracy"]
                               for r in results) / 100, 0.15)

    def test_ambiguous_evidence_abstains(self):
        result = evaluate(1, train_n=1)
        self.assertGreater(result["candidate_count"], 1)
        self.assertLess(result["coverage"], 1)

    def test_replay_and_tamper(self):
        original = evaluate(19)
        recovered = json.loads(json.dumps(original))
        self.assertEqual(digest(original), digest(recovered))
        recovered["transfer_accuracy"] = -1
        self.assertNotEqual(digest(original), digest(recovered))

    def test_invalid_budget(self):
        for kwargs in ({"train_n": 0}, {"test_n": 0}, {"program": (3, 1)}):
            with self.assertRaises(ValueError):
                evaluate(1, **kwargs)


if __name__ == "__main__":
    unittest.main()
