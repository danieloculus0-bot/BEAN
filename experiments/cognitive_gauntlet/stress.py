"""Out-of-family synthetic stress: freeze threshold before new environments.

These conditions differ from training families. No external AI is executed.
"""
import gzip
import hashlib
import json
import os
import random
from pathlib import Path
from .adaptive import VolatilityAdaptiveBelief
from .cognition import Evidence, RevisableBelief

REGIMES = ("weak_stationary", "weak_alternating", "random_drift", "long_stable_then_flip")
RELIABILITY = {"weak_stationary": .55, "weak_alternating": .65,
               "random_drift": .80, "long_stable_then_flip": .85}
ARMS = ("revision", "latest", "adaptive")


def stress(*, first_seed=80, seeds=60, rounds=100, frozen_threshold=.75):
    if not 80 <= first_seed <= 10000 or not 2 <= seeds <= 100 or not 10 <= rounds <= 500:
        raise ValueError("invalid independent stress budget")
    if not 0 <= frozen_threshold <= 1:
        raise ValueError("invalid frozen threshold")
    cases = []
    for regime in REGIMES:
        for seed in range(first_seed, first_seed + seeds):
            rng = random.Random(900001 + seed * 17 + sum(map(ord, regime)))
            truth = rng.randrange(2)
            base = RevisableBelief()
            candidate = VolatilityAdaptiveBelief(threshold=frozen_threshold)
            for step in range(rounds):
                if regime == "weak_alternating" and step:
                    truth = 1 - truth
                elif regime == "random_drift" and step and rng.random() < .12:
                    truth = 1 - truth
                elif regime == "long_stable_then_flip" and step and step % 30 == 0:
                    truth = 1 - truth
                observation = float(truth if rng.random() < RELIABILITY[regime] else 1 - truth)
                evidence = Evidence(f"{regime}:{seed}:{step}", f"sensor-{step%5}", observation, .65)
                base.observe(evidence)
                candidate.observe(evidence)
                predictions = {"revision": base.prediction(),
                               "latest": base.latest_prediction(),
                               "adaptive": candidate.prediction()}
                cases.append({"regime": regime, "seed": seed, "step": step,
                              "truth": truth, "observation": observation,
                              "mode": candidate.mode(), "predictions": predictions,
                              "errors": {k: (v - truth)**2 for k, v in predictions.items()}})
    summary = {}
    for regime in REGIMES:
        rows = [case for case in cases if case["regime"] == regime]
        summary[regime] = {arm: sum(case["errors"][arm] for case in rows) / len(rows)
                           for arm in ARMS}
    report = {"schema": "bean.cognitive_gauntlet.out_of_family.v1",
              "source_revision": os.environ.get("GITHUB_SHA", "local-uncommitted"),
              "threshold_frozen": frozen_threshold,
              "first_seed": first_seed, "seeds": seeds, "rounds": rounds,
              "external_runtimes_executed": [], "cases": cases, "summary": summary,
              "interpretation": "synthetic out-of-family stress; no external AI win"}
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["receipt_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return report


def main():
    result = stress()
    output = Path("cognitive-gauntlet-results/out-of-family.json.gz")
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, sort_keys=True) + "\n").encode()
    output.write_bytes(gzip.compress(raw, mtime=0))
    if gzip.decompress(output.read_bytes()) != raw:
        raise RuntimeError("out-of-family archive failed roundtrip")
    print(json.dumps({"summary": result["summary"],
                      "receipt_sha256": result["receipt_sha256"],
                      "cases": len(result["cases"]), "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
