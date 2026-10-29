"""Independent synthetic heldout: retire stale correlations after verified absence.

Frozen comparator copies the original per-observed-pair decay rule from
main 8c917c526194d0deb4a593f36bf1c60f6fe6f12b. Heldout seeds
71000..71011 do not overlap original dependency heldout 61000..61011.
All observations, predictions, losses and negative controls are retained.
"""
from __future__ import annotations
import gzip
import hashlib
import json
import random
from itertools import combinations
from pathlib import Path
from .sensor_dependency import OnlineDependencyLearner, _Pair
from .sensor_reliability import SensorObservation

REGIMES = ("changed_after_absence", "unchanged_after_absence",
           "unlabeled_absence")
ARMS = ("frozen_pair_only", "global_verified_decay")


class FrozenPairOnlyDecay(OnlineDependencyLearner):
    """Original update rule retained only as a matched control."""

    def learn(self, outcome: int) -> None:
        if self._pending is None:
            raise ValueError("no prediction awaiting feedback")
        if type(outcome) is not int or outcome not in (0, 1):
            raise ValueError("binary verified outcome required")
        wrong = {o.origin: int(o.value != outcome) for o in self._pending}
        for a, b in combinations(sorted(wrong), 2):
            p = self.pairs.setdefault((a, b), _Pair())
            p.n = self.decay * p.n + 1
            p.a_wrong = self.decay * p.a_wrong + wrong[a]
            p.b_wrong = self.decay * p.b_wrong + wrong[b]
            p.both_wrong = self.decay * p.both_wrong + wrong[a] * wrong[b]
        self.trust.learn(outcome)
        self._pending = None


def benchmark(*, seeds=12, warmup=90, absence=120,
              return_steps=100, first_seed=71000):
    if (type(seeds) is not int or not 1 <= seeds <= 24
            or any(type(v) is not int or not 40 <= v <= 200
                   for v in (warmup, absence, return_steps))
            or type(first_seed) is not int or first_seed < 71000):
        raise ValueError("invalid independent heldout budget")
    cases = []
    for regime in REGIMES:
        for seed in range(first_seed, first_seed + seeds):
            rng = random.Random(seed * 101)
            models = {"frozen_pair_only": FrozenPairOnlyDecay(),
                      "global_verified_decay": OnlineDependencyLearner()}
            for step in range(warmup + absence + return_steps):
                truth = rng.randrange(2)
                if step < warmup:
                    phase = "training"
                elif step < warmup + absence:
                    phase = "absence"
                else:
                    phase = "return"
                if phase == "absence":
                    origins = ("s2", "s3", "s4")
                    correct = [rng.random() < .82, rng.random() < .86,
                               rng.random() < .80]
                elif phase == "return" and regime == "changed_after_absence":
                    origins = ("s0", "s1", "s2", "s3", "s4")
                    correct = [rng.random() < .90, rng.random() < .90,
                               rng.random() < .82, rng.random() < .86,
                               rng.random() < .80]
                else:
                    origins = ("s0", "s1", "s2", "s3", "s4")
                    bus = rng.random() < .65
                    correct = [bus, bus, rng.random() < .82,
                               rng.random() < .86, rng.random() < .80]
                observations = [
                    SensorObservation(
                        f"absence:{regime}:{seed}:{step}:{origin}",
                        origin, truth if good else 1 - truth)
                    for origin, good in zip(origins, correct)
                ]
                predictions = {name: model.forecast(observations)
                               for name, model in models.items()}
                groups = {name: dict(model.last_groups)
                          for name, model in models.items()}
                missing = phase == "absence" and regime == "unlabeled_absence"
                losses = {name: (prediction - truth) ** 2
                          for name, prediction in predictions.items()}
                for model in models.values():
                    if missing:
                        model.skip_feedback(reason="outcome_not_attested")
                    else:
                        model.learn(truth)
                assert models["frozen_pair_only"].trust.counts == (
                    models["global_verified_decay"].trust.counts)
                cases.append({
                    "regime": regime, "seed": seed, "step": step,
                    "phase": phase, "observations": [o.__dict__
                                                   for o in observations],
                    "evaluator_truth": truth,
                    "feedback_available": not missing,
                    "groups_before_feedback": groups,
                    "predictions": predictions, "losses": losses,
                })
    scores = {}
    for regime in REGIMES:
        scores[regime] = {}
        for phase in ("training", "absence", "return"):
            rows = [row for row in cases
                    if row["regime"] == regime and row["phase"] == phase]
            scores[regime][phase] = {
                "n": len(rows),
                "missing": sum(not row["feedback_available"] for row in rows),
                "mse": {arm: sum(row["losses"][arm] for row in rows) / len(rows)
                        for arm in ARMS},
                "grouped_return_fraction": {
                    arm: (sum(row["groups_before_feedback"][arm].get("s0")
                              == row["groups_before_feedback"][arm].get("s1")
                              for row in rows) / len(rows))
                    if phase == "return" else None
                    for arm in ARMS
                },
            }
    report = {
        "schema": "bean.gauntlet.sensor_dependency_absence.v1",
        "baseline_source": "8c917c526194d0deb4a593f36bf1c60f6fe6f12b",
        "first_seed": first_seed, "seeds": seeds, "warmup": warmup,
        "absence": absence, "return_steps": return_steps,
        "regimes": list(REGIMES), "cases": cases, "scores": scores,
        "source_feedback": "synthetic_delayed_host_attested",
        "authenticated_provenance": False,
        "production_core_wiring": False,
        "external_runtimes_executed": [],
    }
    raw = json.dumps(report, sort_keys=True, separators=(",", ":"),
                     allow_nan=False)
    report["digest"] = hashlib.sha256(raw.encode()).hexdigest()
    return report


def main():
    report = benchmark()
    out = Path("cognitive-gauntlet-results/sensor-dependency-absence.json.gz")
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, sort_keys=True, allow_nan=False) + "\n").encode()
    out.write_bytes(gzip.compress(raw, mtime=0))
    assert gzip.decompress(out.read_bytes()) == raw
    print(json.dumps({"scores": report["scores"], "digest": report["digest"]},
                     indent=2))


if __name__ == "__main__":
    main()
