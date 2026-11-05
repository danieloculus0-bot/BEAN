"""Synthetic online rule-reversal controls. No BEAN runtime integration."""
import json
import random
import sqlite3
import tempfile
from pathlib import Path


def run(seed=19, n=240, reversal=120):
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory) / "trials.db")
        db = sqlite3.connect(path)
        db.execute("CREATE TABLE observations (trial INTEGER PRIMARY KEY, feature INTEGER, label INTEGER)")
        correct = {"frozen": 0, "cumulative": 0, "recent16": 0}
        post = {key: 0 for key in correct}
        for trial in range(n):
            feature = rng.randrange(2)
            label = feature ^ int(trial >= reversal)
            history = db.execute("SELECT feature,label FROM observations ORDER BY trial").fetchall()

            def predict(samples):
                if not samples:
                    return feature
                flips = sum(x ^ y for x, y in samples)
                return feature ^ int(flips > len(samples) / 2)

            predictions = {"frozen": feature, "cumulative": predict(history),
                           "recent16": predict(history[-16:])}
            for key, prediction in predictions.items():
                hit = int(prediction == label)
                correct[key] += hit
                if trial >= reversal:
                    post[key] += hit
            db.execute("INSERT INTO observations VALUES (?,?,?)", (trial, feature, label))
            db.commit()
            if trial == reversal:
                db.close()
                db = sqlite3.connect(path)  # force actual restart; no model state retained
        assert db.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == n
        db.close()
    return {"seed": seed, "n": n, "reversal": reversal,
            "accuracy": {k: round(v / n, 5) for k, v in correct.items()},
            "post_reversal_accuracy": {k: round(v / (n - reversal), 5) if reversal < n else None
                                       for k, v in post.items()},
            "limitations": "Synthetic binary labels with immediate feedback; not BEAN runtime learning."}


def test_deterministic():
    assert run(19) == run(19)


def test_restart_and_adaptation():
    result = run(19)
    assert result["post_reversal_accuracy"]["recent16"] > result["post_reversal_accuracy"]["cumulative"]
    assert result["post_reversal_accuracy"]["recent16"] > result["post_reversal_accuracy"]["frozen"]


def test_no_shift_control():
    result = run(31, reversal=240)
    assert all(v == 1 for v in result["accuracy"].values())
    assert all(v is None for v in result["post_reversal_accuracy"].values())


def test_fresh_seeds():
    for seed in (37, 53, 101):
        assert run(seed)["post_reversal_accuracy"]["recent16"] >= 0.85


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
