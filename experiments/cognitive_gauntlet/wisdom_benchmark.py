"""Execute frozen five-dimension cognitive audit and archive raw receipts."""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path
from .schrodinger_benchmark import benchmark
from .wisdom_measurement import measure


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--rounds", type=int, default=120)
    parser.add_argument("--first-seed", type=int, default=8000)
    parser.add_argument("--output", type=Path,
                        default=Path("cognitive-gauntlet-results/wisdom-measurement.json.gz"))
    args = parser.parse_args()
    base = benchmark(first_seed=args.first_seed, seeds=args.seeds, rounds=args.rounds)
    measurements = measure(base)
    result = {"schema": "bean.gauntlet.wisdom_with_original_receipts.v1",
              "evidence": base, "measurements": measurements,
              "limits": measurements["limits"],
              "external_runtimes_executed": []}
    raw = (json.dumps(result, sort_keys=True, allow_nan=False) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(gzip.compress(raw, mtime=0))
    if gzip.decompress(args.output.read_bytes()) != raw:
        raise RuntimeError("lossless audit archive verification failed")
    print(json.dumps({
        "cases": measurements["cases_included"],
        "dimensions": {
            "alternative_reasoning": measurements["dimensions"]["alternative_reasoning"]["all"],
            "evidence_judgment": measurements["dimensions"]["evidence_judgment"]["all"],
            "uncertainty_awareness": measurements["dimensions"]["uncertainty_awareness"]["all"],
            "decision_quality": measurements["dimensions"]["decision_quality"]["all"],
            "learning_after_feedback": measurements["dimensions"]["learning_after_feedback"]["all"],
        },
        "audit_sha256": measurements["audit_sha256"],
        "original_receipts_sha256": base["digest"],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
