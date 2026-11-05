"""Synthetic delayed-label online adaptation benchmark; NOT BEAN runtime learning."""
import hashlib
import json
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path


def evaluate(seed=71, n=300, shift=150, delay=8, window=24):
    if not (0 <= delay < n and 0 < shift < n and window > 0):
        raise ValueError("invalid evaluation parameters")
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "evidence.sqlite"
        db = sqlite3.connect(path)
        db.execute("CREATE TABLE trials (t INTEGER PRIMARY KEY, feature INTEGER, label INTEGER, reveal INTEGER)")
        results = {k: [0, 0] for k in ("frozen", "cumulative", "recent")}
        trace = []
        for t in range(n):
            feature = rng.randrange(2)
            # Hidden rule reversal. Predictions never receive the shift flag.
            label = feature ^ int(t >= shift)
            visible = db.execute("SELECT feature,label FROM trials WHERE reveal <= ? ORDER BY t", (t,)).fetchall()

            def vote(rows):
                if not rows:
                    return feature
                flips = sum(a ^ b for a, b in rows)
                return feature ^ int(2 * flips > len(rows))

            guesses = {"frozen": feature, "cumulative": vote(visible),
                       "recent": vote(visible[-window:])}
            for name, guess in guesses.items():
                results[name][int(t >= shift)] += int(guess == label)
            trace.append((t, feature, label, len(visible), guesses))
            # Reveal only after this and 'delay' additional predictions.
            db.execute("INSERT INTO trials VALUES (?,?,?,?)", (t, feature, label, t + delay + 1))
            db.commit()
            if t == shift:
                db.close()
                db = sqlite3.connect(path)
        assert db.execute("SELECT COUNT(*) FROM trials").fetchone()[0] == n
        db.close()
    return {"seed": seed, "delay": delay, "window": window,
            "pre": {k: v[0] / shift for k, v in results.items()},
            "post": {k: v[1] / (n-shift) for k, v in results.items()},
            "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest()}


class DelayedFeedbackTests(unittest.TestCase):
    def test_replay_determinism_and_restart(self):
        self.assertEqual(evaluate(), evaluate())

    def test_delayed_feedback_vs_immediate(self):
        immediate = evaluate(delay=0)
        delayed = evaluate(delay=16)
        self.assertGreater(immediate["post"]["recent"], delayed["post"]["recent"])
        self.assertGreater(delayed["post"]["recent"], delayed["post"]["cumulative"])

    def test_no_future_label_available(self):
        result = evaluate(n=100, shift=50, delay=99)
        self.assertEqual(result["post"]["recent"], 0)
        self.assertEqual(result["post"]["cumulative"], 0)

    def test_fresh_seeds(self):
        for seed in (72, 73, 74):
            result = evaluate(seed=seed)
            self.assertGreater(result["post"]["recent"], result["post"]["cumulative"])


if __name__ == "__main__":
    unittest.main()
