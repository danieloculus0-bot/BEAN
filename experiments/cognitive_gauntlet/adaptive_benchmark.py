"""Train/held-out synthetic duel with complete per-case receipts.

Selection sees only training labels. Each candidate predictor receives only
past/current noisy observations, never scenario, truth, or future samples.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
from .adaptive import VolatilityAdaptiveBelief
from .arena import run as original_arena
from .cognition import Evidence

THRESHOLDS = (0.45, 0.55, 0.65, 0.75, 0.85)
SCENARIOS = ("stationary", "drifting", "rapid_drift")
ARMS = ("bean_revision", "bean_latest", "bean_adaptive")


def _evaluate(cases, threshold, *, keep_cases=False):
    models = {}
    losses = {scenario: {arm: 0.0 for arm in ARMS} for scenario in SCENARIOS}
    counts = {scenario: 0 for scenario in SCENARIOS}
    receipts = []
    for case in cases:
        scenario, seed = case["scenario"], case["seed"]
        model = models.setdefault((scenario, seed), VolatilityAdaptiveBelief(threshold=threshold))
        model.observe(Evidence(case["evidence_id"], case["origin"], float(case["observation"]), 0.65))
        estimates = {**case["estimates"], "bean_adaptive": model.prediction()}
        errors = {arm: (estimates[arm] - case["ground_truth"]) ** 2 for arm in ARMS}
        for arm in ARMS:
            losses[scenario][arm] += errors[arm]
        counts[scenario] += 1
        if keep_cases:
            receipts.append({**case, "estimates": estimates,
                             "squared_error": errors, "adaptive_mode": model.mode(),
                             "volatility": model.volatility()})
    summary = {scenario: {"n": counts[scenario], "mse": {
        arm: losses[scenario][arm] / counts[scenario] for arm in ARMS}}
        for scenario in SCENARIOS}
    aggregate = {arm: sum(losses[scenario][arm] for scenario in SCENARIOS) /
                 sum(counts.values()) for arm in ARMS}
    return {"by_scenario": summary, "aggregate_mse": aggregate, "cases": receipts}


def benchmark(*, seeds=80, training_seeds=20, rounds=100):
    if type(seeds) is not int or type(training_seeds) is not int or not 4 <= seeds <= 250 or not 2 <= training_seeds <= seeds - 2:
        raise ValueError("need disjoint training and held-out seeds")
    if type(rounds) is not int or not 8 <= rounds <= 500:
        raise ValueError("invalid rounds")
    original = original_arena(seeds=seeds, rounds=rounds)
    train = [r for r in original["cases"] if r["seed"] < training_seeds]
    holdout = [r for r in original["cases"] if r["seed"] >= training_seeds]
    train_scores = {str(t): _evaluate(train, t)["aggregate_mse"]["bean_adaptive"]
                    for t in THRESHOLDS}
    selected = min(THRESHOLDS, key=lambda t: (train_scores[str(t)], t))
    training = _evaluate(train, selected, keep_cases=True)
    blind = _evaluate(holdout, selected, keep_cases=True)
    result = {
        "schema": "bean.cognitive_gauntlet.adaptive_heldout.v1",
        "source_revision": os.environ.get("GITHUB_SHA", "local-uncommitted"),
        "original_arena_digest": original["evidence_sha256"],
        "source": "original seeded synthetic arena, no external AI runtimes",
        "external_runtimes_executed": [],
        "protocol": "threshold chosen on seeds [0,training_seeds); frozen on heldout seeds; only observations to predictor",
        "seed_count": seeds, "training_seeds": training_seeds, "rounds": rounds,
        "threshold_candidates": list(THRESHOLDS), "train_candidate_mse": train_scores,
        "selected_threshold": selected,
        "training": training, "heldout": blind,
        "interpretation": "synthetic heuristic adaptation only; no external architecture defeated",
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    result["receipt_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=80)
    parser.add_argument("--training-seeds", type=int, default=20)
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("cognitive-gauntlet-results/adaptive-heldout.json.gz"))
    args = parser.parse_args()
    result = benchmark(seeds=args.seeds, training_seeds=args.training_seeds, rounds=args.rounds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    args.output.write_bytes(gzip.compress(raw, mtime=0))
    if gzip.decompress(args.output.read_bytes()) != raw:
        raise RuntimeError("lossless evidence archive verification failed")
    print(json.dumps({"selected_threshold": result["selected_threshold"],
                      "training_mse": result["training"]["aggregate_mse"],
                      "heldout_mse": result["heldout"]["aggregate_mse"],
                      "heldout_by_scenario": result["heldout"]["by_scenario"],
                      "receipt_sha256": result["receipt_sha256"],
                      "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
