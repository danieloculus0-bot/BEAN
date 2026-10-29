"""Independent synthetic heldout for unavailable and selectively missing labels.

Frozen hyperparameters; the evaluator knows truth, but the forecast and skip
paths never receive it. Every forecast, failure and skipped label is archived.
"""
import gzip
import hashlib
import json
import random
from pathlib import Path
from .sensor_reliability import OnlineSensorTrust, SensorObservation

REGIMES = ("diverse_random", "swap_random", "diverse_selective", "swap_selective")
ARMS = ("fixed_prior", "full_feedback", "missing_feedback", "unweighted")


def benchmark(*, seeds=12, rounds=100, first_seed=26000):
    if (type(seeds) is not int or type(rounds) is not int or type(first_seed) is not int
            or not 1 <= seeds <= 30 or not 20 <= rounds <= 200 or first_seed < 26000):
        raise ValueError("invalid independent heldout budget")
    cases = []
    for regime in REGIMES:
        for seed in range(first_seed, first_seed + seeds):
            rng = random.Random(seed * 67 + sum(map(ord, regime)) * 101)
            truth = rng.randrange(2)
            oracle = OnlineSensorTrust(decay=.97)
            partial = OnlineSensorTrust(decay=.97)
            for step in range(rounds):
                if step and rng.random() < .08:
                    truth ^= 1
                probs = ((.9, .85, .8, .7, .65) if regime.startswith("diverse")
                         else ((.88, .82, .78, .25, .12) if step < rounds // 2
                               else (.12, .25, .28, .82, .9)))
                observations = [SensorObservation(
                    f"missing:{regime}:{seed}:{step}:{i}", f"s{i}",
                    truth if rng.random() < p else 1 - truth)
                    for i, p in enumerate(probs)]
                # The selective mechanism is outcome-dependent *in the host*.
                # The learner sees only that feedback was unavailable.
                wrong_votes = sum(o.value != truth for o in observations)
                unavailable = (rng.random() < .35 if regime.endswith("random")
                               else wrong_votes >= 3 or rng.random() < .10)
                fixed = OnlineSensorTrust()
                predictions = {
                    "fixed_prior": fixed.forecast(observations),
                    "full_feedback": oracle.forecast(observations),
                    "missing_feedback": partial.forecast(observations),
                    "unweighted": sum(o.value for o in observations) / len(observations),
                }
                before = dict(partial.counts)
                losses = {name: (value - truth) ** 2
                          for name, value in predictions.items()}
                if unavailable:
                    partial.skip_feedback(reason="host_outcome_unavailable")
                    assert partial.counts == before, "missing feedback altered trust"
                else:
                    partial.learn(truth)
                oracle.learn(truth)
                fixed.learn(truth)
                cases.append({"regime": regime, "seed": seed, "step": step,
                              "evidence": [o.__dict__ for o in observations],
                              "feedback_available": not unavailable,
                              "missing_reason": "host_outcome_unavailable" if unavailable else None,
                              "evaluator_truth": truth, "wrong_votes": wrong_votes,
                              "predictions": predictions, "losses": losses,
                              "trust_counts_before_feedback": before,
                              "trust_counts_after_feedback": dict(partial.counts)})
    scores = {}
    for regime in (*REGIMES, "all"):
        rows = [x for x in cases if regime == "all" or x["regime"] == regime]
        scores[regime] = {"n": len(rows),
                          "missing": sum(not x["feedback_available"] for x in rows),
                          "mse": {arm: sum(x["losses"][arm] for x in rows) / len(rows)
                                  for arm in ARMS}}
    report = {"schema": "bean.gauntlet.sensor_missing_feedback.v1",
              "heldout_first_seed": first_seed, "seeds": seeds, "rounds": rounds,
              "regimes": list(REGIMES), "cases": cases, "scores": scores,
              "external_runtimes_executed": [],
              "source_feedback": "synthetic_host_attested_not_independently_verified",
              "full_feedback_arm": "unavailable_oracle_control_not_deployable",
              "policy_tuning_on_heldout": False}
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["digest"] = hashlib.sha256(payload.encode()).hexdigest()
    return report


def main():
    report = benchmark()
    path = Path("cognitive-gauntlet-results/sensor-missing-feedback.json.gz")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, sort_keys=True, allow_nan=False) + "\n").encode()
    path.write_bytes(gzip.compress(raw, mtime=0))
    assert gzip.decompress(path.read_bytes()) == raw
    print(json.dumps({"scores": report["scores"], "digest": report["digest"]}, indent=2))


if __name__ == "__main__":
    main()
