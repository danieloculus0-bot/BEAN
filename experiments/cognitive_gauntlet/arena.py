"""Head-to-head microbenchmark: experimental BEAN revision vs BEAN latest.

Both arms receive identical evidence and are scored on unseen outcomes.
Other external projects are NOT claimed as executed opponents.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import random
from .cognition import Evidence, RevisableBelief


def run(*, seeds=25, rounds=30):
    if not 2 <= seeds <= 250 or not 4 <= rounds <= 500:
        raise ValueError("invalid test budget")
    records = []
    for scenario in ("stationary", "drifting"):
        for seed in range(seeds):
            rng = random.Random(120011 + seed * 31 + (0 if scenario == "stationary" else 900001))
            truth = rng.randrange(2)
            model = RevisableBelief()
            for step in range(rounds):
                if scenario == "drifting" and step and step % 7 == 0:
                    truth = 1 - truth
                # The environment generates real measured labels, unseen by both arms.
                origin = "sensor-" + str(step % 5)
                frequency = truth if rng.random() < 0.72 else 1 - truth
                model.observe(Evidence(f"{scenario}:{seed}:{step}", origin,
                                       float(frequency), 0.65))
                estimates = {"bean_revision": model.prediction(),
                             "bean_latest": model.latest_prediction()}
                records.append({
                    "scenario": scenario, "seed": seed, "step": step,
                    "ground_truth": truth, "evidence_id": model.history[-1].event_id,
                    "origin": origin, "observation": frequency,
                    "estimates": estimates,
                    "squared_error": {k: round((v - truth) ** 2, 12)
                                      for k, v in estimates.items()},
                })
    scores = {}
    for scenario in ("stationary", "drifting"):
        cases = [r for r in records if r["scenario"] == scenario]
        averages = {arm: sum(r["squared_error"][arm] for r in cases) / len(cases)
                    for arm in ("bean_revision", "bean_latest")}
        wins = sum(r["squared_error"]["bean_revision"] < r["squared_error"]["bean_latest"]
                   for r in cases)
        losses = sum(r["squared_error"]["bean_revision"] > r["squared_error"]["bean_latest"]
                     for r in cases)
        scores[scenario] = {
            "n": len(cases), "mse": averages,
            "revision_better_cases": wins, "revision_worse_cases": losses,
            "ties": len(cases) - wins - losses,
            "verdict": "revision" if averages["bean_revision"] < averages["bean_latest"]
            else "latest" if averages["bean_revision"] > averages["bean_latest"] else "tie",
        }
    payload = {
        "schema": "bean.cognitive_gauntlet.belief_microbenchmark.v1",
        "source": "seeded synthetic noisy binary observations",
        "arms": ["bean_revision", "bean_latest"],
        "external_runtimes_executed": [],
        "seeds": seeds, "rounds": rounds,
        "scoring": "mean squared error; lower is better",
        "scoreboard": scores, "cases": records,
        "interpretation": "bounded belief-revision comparison only; no AGI or external-system superiority evidence",
    }
    serial = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    payload["evidence_sha256"] = hashlib.sha256(serial.encode()).hexdigest()
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=25)
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--output", type=Path,
                        default=Path("cognitive-gauntlet-results/duel.json.gz"))
    args = parser.parse_args()
    result = run(seeds=args.seeds, rounds=args.rounds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    if args.output.suffix == ".gz":
        args.output.write_bytes(gzip.compress(raw, mtime=0))
    else:
        args.output.write_bytes(raw)
    print(json.dumps({"scores": result["scoreboard"],
                      "evidence_sha256": result["evidence_sha256"],
                      "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
