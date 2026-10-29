"""Predeclared synthetic heldout for delayed-feedback source-dependency learning.

Exploratory seeds 51000..51011. Evaluation starts at 61000; no evaluation
outcome may enter the same forecast's grouping. Retain all cases and failures.
"""
from __future__ import annotations
import gzip
import hashlib
import json
import random
from pathlib import Path
from .sensor_reliability import OnlineSensorTrust, SensorObservation
from .sensor_dependency import OnlineDependencyLearner

REGIMES = ("shared_bus", "independent", "two_buses", "selective_missing",
           "shared_weak", "correlation_reversal")
ARMS = ("ungrouped", "learned_dependency", "oracle_grouped")


def benchmark(*, seeds=12, rounds=120, first_seed=61000):
    if (type(seeds) is not int or not 1 <= seeds <= 24
            or type(rounds) is not int or not 40 <= rounds <= 160
            or type(first_seed) is not int or first_seed < 61000):
        raise ValueError("invalid heldout budget")
    cases = []
    for regime in REGIMES:
        for seed in range(first_seed, first_seed + seeds):
            rng = random.Random(seed * 83 + sum(map(ord, regime)) * 127)
            truth = rng.randrange(2)
            baseline = OnlineSensorTrust(decay=.97)
            candidate = OnlineDependencyLearner()
            oracle = OnlineSensorTrust(decay=.97)
            for step in range(rounds):
                if step and rng.random() < .08:
                    truth ^= 1
                if regime == "two_buses":
                    bus_a, bus_b = rng.random() < .78, rng.random() < .66
                    correct = [bus_a, bus_a, bus_b, bus_b, rng.random() < .86]
                    groups = {"s0": "bus_a", "s1": "bus_a", "s2": "bus_b",
                              "s3": "bus_b", "s4": "independent"}
                elif regime in ("shared_bus", "shared_weak", "selective_missing",
                                "correlation_reversal"):
                    # The final regime changes to independent sources halfway.
                    independent = regime == "correlation_reversal" and step >= rounds // 2
                    if independent:
                        correct = [rng.random() < .77 for _ in range(3)]
                    else:
                        bus = rng.random() < (.56 if regime == "shared_weak" else .77)
                        correct = [bus] * 3
                    correct += [rng.random() < .82, rng.random() < .86]
                    groups = {f"s{i}": ("bus" if i < 3 and not independent else f"s{i}")
                              for i in range(5)}
                else:
                    correct = [rng.random() < .77 for _ in range(3)]
                    correct += [rng.random() < .82, rng.random() < .86]
                    groups = {f"s{i}": f"s{i}" for i in range(5)}
                observations = [SensorObservation(f"dep:{regime}:{seed}:{step}:{i}",
                                                  f"s{i}", truth if good else 1 - truth)
                                for i, good in enumerate(correct)]
                preds = {
                    "ungrouped": baseline.forecast(observations),
                    "learned_dependency": candidate.forecast(observations),
                    "oracle_grouped": oracle.forecast(observations,
                                                       provenance_groups=groups),
                }
                inferred = dict(candidate.last_groups)
                losses = {name: (value - truth) ** 2 for name, value in preds.items()}
                missing = (regime == "selective_missing" and
                           (sum(not x for x in correct) >= 3 or rng.random() < .10))
                if missing:
                    baseline.skip_feedback(reason="host_outcome_unavailable")
                    candidate.skip_feedback(reason="host_outcome_unavailable")
                    oracle.skip_feedback(reason="host_outcome_unavailable")
                else:
                    baseline.learn(truth)
                    candidate.learn(truth)
                    oracle.learn(truth)
                assert baseline.counts == candidate.trust.counts == oracle.counts
                cases.append({"regime": regime, "seed": seed, "step": step,
                              "observations": [o.__dict__ for o in observations],
                              "evaluator_truth": truth, "oracle_groups": groups,
                              "inferred_groups_before_feedback": inferred,
                              "feedback_available": not missing,
                              "predictions": preds, "losses": losses})
    scores = {}
    for regime in (*REGIMES, "all"):
        rows = [r for r in cases if regime == "all" or r["regime"] == regime]
        scores[regime] = {"n": len(rows),
                          "missing": sum(not r["feedback_available"] for r in rows),
                          "mse": {arm: sum(r["losses"][arm] for r in rows) / len(rows)
                                  for arm in ARMS}}
    report = {"schema": "bean.gauntlet.sensor_dependency.v1",
              "first_seed": first_seed, "seeds": seeds, "rounds": rounds,
              "regimes": list(REGIMES), "cases": cases, "scores": scores,
              "source_feedback": "synthetic_delayed_host_attested",
              "authenticated_provenance": False,
              "production_core_wiring": False,
              "external_runtimes_executed": [],
              "interpretation": "inferred error correlation is not proof of common origin"}
    raw = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["digest"] = hashlib.sha256(raw.encode()).hexdigest()
    return report


def main():
    report = benchmark()
    out = Path("cognitive-gauntlet-results/sensor-dependency.json.gz")
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, sort_keys=True, allow_nan=False) + "\n").encode()
    out.write_bytes(gzip.compress(raw, mtime=0))
    assert gzip.decompress(out.read_bytes()) == raw
    print(json.dumps({"scores": report["scores"], "digest": report["digest"]}, indent=2))


if __name__ == "__main__":
    main()
