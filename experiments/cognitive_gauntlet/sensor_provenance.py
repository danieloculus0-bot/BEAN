"""Predeclared independent synthetic provenance grouping evaluation.

This does not infer or authenticate shared sources. The host asserts groups;
truth is withheld until AFTER each forecast, and all failures are retained.
Exploratory design seeds: 31000..31011. Evaluation seeds start at 41000.
"""
from __future__ import annotations
import gzip
import hashlib
import json
import random
from pathlib import Path
from .sensor_reliability import OnlineSensorTrust, SensorObservation

REGIMES = ("shared_bus", "shared_weak", "independent", "false_group",
           "selective_missing", "two_buses")
ARMS = ("ungrouped", "provenance_grouped")


def benchmark(*, seeds=12, rounds=100, first_seed=41000):
    if (type(seeds) is not int or type(rounds) is not int or type(first_seed) is not int
            or not 1 <= seeds <= 30 or not 20 <= rounds <= 200
            or first_seed < 41000):
        raise ValueError("invalid independent heldout budget")
    cases = []
    for regime in REGIMES:
        for seed in range(first_seed, first_seed + seeds):
            rng = random.Random(seed * 71 + sum(map(ord, regime)) * 113)
            truth = rng.randrange(2)
            baseline = OnlineSensorTrust(decay=.97)
            candidate = OnlineSensorTrust(decay=.97)
            for step in range(rounds):
                if step and rng.random() < .08:
                    truth ^= 1
                if regime == "shared_weak":
                    p0, p1, p2 = .56, .72, .82
                else:
                    p0, p1, p2 = .77, .82, .86
                if regime == "two_buses":
                    bus0 = rng.random() < .78
                    bus1 = rng.random() < .65
                    correct = [bus0, bus0, bus1, bus1, rng.random() < .86]
                elif regime in ("shared_bus", "shared_weak", "selective_missing"):
                    shared = rng.random() < p0
                    correct = [shared, shared, shared, rng.random() < p1,
                               rng.random() < p2]
                else:
                    correct = [rng.random() < p0 for _ in range(3)]
                    correct.extend([rng.random() < p1, rng.random() < p2])
                observations = [
                    SensorObservation(f"provenance:{regime}:{seed}:{step}:{i}",
                                      f"s{i}", truth if good else 1 - truth)
                    for i, good in enumerate(correct)]
                if regime == "two_buses":
                    groups = {"s0": "bus0", "s1": "bus0", "s2": "bus1",
                              "s3": "bus1", "s4": "s4"}
                else:
                    groups = {f"s{i}": ("shared" if i < 3 and regime != "independent"
                                        else f"s{i}") for i in range(5)}
                predictions = {
                    "ungrouped": baseline.forecast(observations),
                    "provenance_grouped": candidate.forecast(
                        observations, provenance_groups=groups)}
                losses = {arm: (prediction - truth) ** 2
                          for arm, prediction in predictions.items()}
                # Missingness depends on evaluator truth, never learner input.
                unavailable = (regime == "selective_missing"
                               and (sum(not good for good in correct) >= 3
                                    or rng.random() < .10))
                before = dict(candidate.counts)
                if unavailable:
                    baseline.skip_feedback(reason="host_outcome_unavailable")
                    candidate.skip_feedback(reason="host_outcome_unavailable")
                    assert candidate.counts == before
                else:
                    baseline.learn(truth)
                    candidate.learn(truth)
                assert baseline.counts == candidate.counts
                cases.append({
                    "regime": regime, "seed": seed, "step": step,
                    "evidence": [o.__dict__ for o in observations],
                    "host_asserted_provenance_groups": groups,
                    "evaluator_truth": truth,
                    "feedback_available": not unavailable,
                    "missing_reason": "host_outcome_unavailable" if unavailable else None,
                    "predictions": predictions, "losses": losses,
                    "trust_counts_before_feedback": before,
                    "trust_counts_after_feedback": dict(candidate.counts)})
    scores = {}
    for regime in (*REGIMES, "all"):
        rows = [row for row in cases
                if regime == "all" or row["regime"] == regime]
        scores[regime] = {
            "n": len(rows),
            "missing": sum(not row["feedback_available"] for row in rows),
            "mse": {arm: sum(row["losses"][arm] for row in rows) / len(rows)
                    for arm in ARMS}}
    report = {
        "schema": "bean.gauntlet.sensor_provenance.v1",
        "first_seed": first_seed, "seeds": seeds, "rounds": rounds,
        "regimes": list(REGIMES), "cases": cases, "scores": scores,
        "external_runtimes_executed": [],
        "host_groups_authenticated": False,
        "source_feedback": "synthetic_host_attested_not_independently_verified",
        "policy_tuning_on_evaluation_seeds": False,
        "interpretation": "grouping is supplied provenance, not inferred correlation"}
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"),
                         allow_nan=False)
    report["digest"] = hashlib.sha256(payload.encode()).hexdigest()
    return report


def main():
    report = benchmark()
    path = Path("cognitive-gauntlet-results/sensor-provenance.json.gz")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, sort_keys=True, allow_nan=False) + "\n").encode()
    path.write_bytes(gzip.compress(raw, mtime=0))
    assert gzip.decompress(path.read_bytes()) == raw
    print(json.dumps({"scores": report["scores"], "digest": report["digest"]},
                     indent=2))


if __name__ == "__main__":
    main()
