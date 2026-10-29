"""Schrodinger's Logic fair replay using original BEAN sensor-duel cases.

Frozen chaos selection thresholds. Every event is first predicted independently
by both existing learners, and only afterwards receives its original outcome.
The original control scores are untouched, with per-case parity assertions.
"""
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
from .sensor_benchmark import benchmark as reference_benchmark, REGIMES
from .sensor_reliability import SensorObservation
from .schrodingers_logic import SchrodingersLogic
from .decision_audit import audit_cases

ARMS = ("fixed_prior", "long_memory", "forgetful", "unweighted", "schrodingers_logic")


def benchmark(*, first_seed=8000, seeds=30, rounds=120):
    if (type(first_seed) is not int or first_seed < 8000 or
            type(seeds) is not int or not 1 <= seeds <= 100 or
            type(rounds) is not int or not 20 <= rounds <= 400):
        raise ValueError("invalid independent replay budget")
    reference = reference_benchmark(seeds=seeds, rounds=rounds, first_seed=first_seed)
    models = {}
    cases = []
    for source in reference["cases"]:
        key = (source["regime"], source["seed"])
        if key not in models:
            models[key] = SchrodingersLogic()
        model = models[key]
        observation = [SensorObservation(**entry) for entry in source["evidence"]]
        prediction = model.forecast(observation)
        diagnostic = model.diagnostics()
        for new, old in (("long_prediction", "long_memory"),
                         ("short_prediction", "forgetful")):
            if not math.isclose(diagnostic[new], source["predictions"][old],
                                rel_tol=1e-12, abs_tol=1e-12):
                raise AssertionError("matched baseline diverged: " + str(key))
        forecasts = {**source["predictions"], "schrodingers_logic": prediction}
        outcome = source["revealed_outcome"]
        losses = {name: (value - outcome) ** 2 for name, value in forecasts.items()}
        cases.append({
            "regime": source["regime"], "seed": source["seed"], "step": source["step"],
            "evidence": source["evidence"], "truth_revealed_after_forecast": outcome,
            "predictions": forecasts, "losses": losses,
            "mode": diagnostic["mode"],
            "chaos_evidence": {"recent_short_advantage": diagnostic["recent_advantage"],
                               "source_reliability_gap": diagnostic["source_gap"]},
        })
        model.learn(outcome)
    score = {}
    for regime in (*REGIMES, "all"):
        rows = [x for x in cases if regime == "all" or x["regime"] == regime]
        score[regime] = {
            "cases": len(rows),
            "chaos_cases": sum(x["mode"] == "parallel_chaos" for x in rows),
            "mse": {name: sum(x["losses"][name] for x in rows) / len(rows)
                    for name in ARMS},
        }
        for name in ARMS[:-1]:
            if not math.isclose(score[regime]["mse"][name],
                                reference["scores"][regime]["mse"][name],
                                rel_tol=1e-12, abs_tol=1e-12):
                raise AssertionError("reference score changed: " + name)
    report = {
        "schema": "bean.gauntlet.schrodingers_logic.v1",
        "source_revision": os.environ.get("GITHUB_SHA", "local-uncommitted"),
        "reference_digest": reference["digest"],
        "first_seed": first_seed, "seeds": seeds, "rounds": rounds,
        "output_rule": "long-memory alone when calm; preserve two hypotheses and blend only during evidence-backed chaos",
        "chaos_parameters": {"short_decay": .97, "window": 12,
                             "min_history": 18, "entry_advantage": .025,
                             "exit_advantage": -.005, "entry_gap": .075,
                             "exit_gap": .035, "short_weight": .80},
        "external_runtimes_executed": [],
        "truth_given_only_after_forecast": True,
        "interpretation": "synthetic parallel-state hypothesis experiment, not quantum mechanics or AGI",
        "scores": score, "cases": cases,
        "decision_quality": audit_cases(cases, ARMS, source_digest=reference["digest"]),
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["digest"] = hashlib.sha256(canonical.encode()).hexdigest()
    return report


def main():
    report = benchmark()
    target = Path("cognitive-gauntlet-results/schrodingers-logic.json.gz")
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, sort_keys=True, allow_nan=False) + "\n").encode()
    target.write_bytes(gzip.compress(raw, mtime=0))
    if gzip.decompress(target.read_bytes()) != raw:
        raise RuntimeError("evidence archive did not round-trip")
    print(json.dumps({"scores": report["scores"], "digest": report["digest"],
                      "source_revision": report["source_revision"]}, indent=2))


if __name__ == "__main__":
    main()
