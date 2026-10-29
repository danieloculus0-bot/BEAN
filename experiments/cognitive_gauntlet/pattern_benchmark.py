"""Frozen-parameter synthetic rematch with complete case-level receipts.

Parameters were chosen on original arena seeds 0..19 only. Held-out
and additional families are evaluation, NOT further training. No external
AGI runtime runs in this experiment.
"""
from __future__ import annotations
import gzip
import hashlib
import json
import os
import random
from pathlib import Path
from .arena import run as original_arena
from .cognition import Evidence, RevisableBelief
from .adaptive import VolatilityAdaptiveBelief
from .pattern_bayes import PatternMixtureBelief

PARAMETERS = {"window": 11, "prior_alternating": .10,
              "reliability_alpha": 3., "reliability_beta": 1.}
REGIMES = ("weak_stationary", "weak_alternating", "random_drift",
           "long_stable_then_flip", "new_noisy_stationary",
           "new_rapid_alternating", "new_irregular_jumps", "new_burst_noise")
ARMS = ("revision", "latest", "volatility_adaptive", "pattern_mixture")


def _fresh_rows(*, first_seed=400, seeds=40, rounds=120):
    for regime in REGIMES:
        for seed in range(first_seed, first_seed + seeds):
            rng = random.Random(900001 + seed * 17 + sum(map(ord, regime)))
            truth = rng.randrange(2)
            for step in range(rounds):
                if regime in ("weak_alternating", "new_rapid_alternating") and step:
                    truth ^= 1
                elif regime == "random_drift" and step and rng.random() < .12:
                    truth ^= 1
                elif regime in ("long_stable_then_flip", "new_irregular_jumps") and step and step % (30 if regime == "long_stable_then_flip" else 43) == 0:
                    truth ^= 1
                elif regime == "new_burst_noise" and step and 20 <= step % 60 < 35:
                    truth ^= 1
                reliability = {"weak_stationary": .55, "weak_alternating": .65,
                               "random_drift": .80, "long_stable_then_flip": .85,
                               "new_noisy_stationary": .53, "new_rapid_alternating": .96,
                               "new_irregular_jumps": .80, "new_burst_noise": .70}[regime]
                observation = float(truth if rng.random() < reliability else 1 - truth)
                yield {"family": regime, "seed": seed, "step": step,
                       "ground_truth": truth, "origin": f"sensor-{step%5}",
                       "observation": observation,
                       "evidence_id": f"new:{regime}:{seed}:{step}"}


def _assess(cases):
    groups = {}
    receipts = []
    for case in cases:
        key = (case["family"], case["seed"])
        if key not in groups:
            groups[key] = (RevisableBelief(),
                           VolatilityAdaptiveBelief(threshold=.75),
                           PatternMixtureBelief(**PARAMETERS))
        fixed, adaptive, mixture = groups[key]
        evidence = Evidence(case["evidence_id"], case["origin"],
                            float(case["observation"]), .65)
        for model in (fixed, adaptive, mixture):
            model.observe(evidence)
        predictions = {"revision": fixed.prediction(),
                       "latest": fixed.latest_prediction(),
                       "volatility_adaptive": adaptive.prediction(),
                       "pattern_mixture": mixture.prediction()}
        errors = {name: (value - case["ground_truth"]) ** 2
                  for name, value in predictions.items()}
        receipts.append({**case, "predictions": predictions,
                         "squared_error": errors,
                         "pattern_posterior": mixture.pattern_posterior(),
                         "adaptive_mode": adaptive.mode()})
    summary = {}
    for family in sorted({case["family"] for case in receipts}):
        subset = [case for case in receipts if case["family"] == family]
        summary[family] = {"n": len(subset),
                           "mse": {arm: sum(c["squared_error"][arm] for c in subset) / len(subset)
                                   for arm in ARMS}}
    summary["all"] = {"n": len(receipts),
                      "mse": {arm: sum(c["squared_error"][arm] for c in receipts) / len(receipts)
                              for arm in ARMS}}
    return {"summary": summary, "cases": receipts}


def benchmark(*, heldout_start=20, heldout_seeds=60, rounds=100,
              fresh_start=400, fresh_seeds=40, fresh_rounds=120):
    if not (heldout_start >= 20 and 1 <= heldout_seeds <= 100 and 8 <= rounds <= 500
            and fresh_start >= 400 and 1 <= fresh_seeds <= 100 and 10 <= fresh_rounds <= 500):
        raise ValueError("invalid split/budget")
    original = original_arena(seeds=heldout_start + heldout_seeds, rounds=rounds)
    heldout = [dict(family=c["scenario"], seed=c["seed"], step=c["step"],
                    ground_truth=c["ground_truth"], origin=c["origin"],
                    observation=c["observation"], evidence_id=c["evidence_id"])
               for c in original["cases"] if c["seed"] >= heldout_start]
    report = {"schema": "bean.cognitive_gauntlet.pattern_mixture.v1",
              "source_revision": os.environ.get("GITHUB_SHA", "local-uncommitted"),
              "parameters": PARAMETERS,
              "parameter_source": "original training seeds 0..19, frozen before evaluation",
              "heldout_original": _assess(heldout),
              "additional_synthetic_families": _assess(_fresh_rows(
                  first_seed=fresh_start, seeds=fresh_seeds, rounds=fresh_rounds)),
              "heldout_seed_range": [heldout_start, heldout_start + heldout_seeds],
              "additional_seed_range": [fresh_start, fresh_start + fresh_seeds],
              "external_runtimes_executed": [],
              "interpretation": "synthetic observation-only algorithm comparison; not AGI"}
    raw = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["receipt_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    return report


def main():
    result = benchmark()
    path = Path("cognitive-gauntlet-results/pattern-mixture.json.gz")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, sort_keys=True, allow_nan=False) + "\n").encode()
    path.write_bytes(gzip.compress(raw, mtime=0))
    if gzip.decompress(path.read_bytes()) != raw:
        raise RuntimeError("archive failed round-trip")
    print(json.dumps({
        "original_heldout": result["heldout_original"]["summary"],
        "additional_families": result["additional_synthetic_families"]["summary"],
        "case_count": (len(result["heldout_original"]["cases"])
                       + len(result["additional_synthetic_families"]["cases"])),
        "receipt_sha256": result["receipt_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
