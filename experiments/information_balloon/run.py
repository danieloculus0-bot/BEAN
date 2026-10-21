"""Reproducible synthetic Balloon experiment. No real or private input is stored."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bean.optimization.information_balloon import canonical, run_experiment


def fixture():
    tags = ["inspection", "maintenance", "scheduling", "estimation"]
    out = []
    for index in range(36):
        topic = tags[index % len(tags)]
        # Synthetic repeated ledger records with deliberate unique details.
        sentence = (f"trial={index:03d};category={topic};evidence=synthetic;"
                    f"source=simulated-input;SHA-tag={index*index+3:06d};")
        out.append({"id": f"E{index:05d}",
                    "tags": [topic, "ledger", "failed" if index % 7 == 0 else "passed"],
                    "text": sentence * (10 + index % 5)})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = fixture()
    seeds = (3, 13, 29)
    runs = []
    for seed in seeds:
        runs.append(run_experiment(
            records,archive_budget=3500,context_budget=2048,
            queries=["inspection","maintenance","scheduling","estimation"],
            min_recall=1.0,iterations=16,seed=seed))
    report = {
        "schema": "bean.balloon.study.v1", "evidence": "synthetic",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(canonical(records)).hexdigest(),
        "source_records":len(records),
        "environment":{"python":platform.python_version(),"os":platform.system(),
                       "arch":platform.machine(),
                       "source_revision":os.environ.get("GITHUB_SHA","local_unpinned")},
        "notes": [
            "Time/ratios are measured only on this CI worker, not transferable benchmarks",
            "All heldout metrics use disjoint dataset partitions, not real-world generalization",
            "Weissman-style unit-normalized diagnostic is not the canonical Weissman Score",
            "Complete source bytes stay outside the working context shelf; no retention deletion",
            "HMAC authenticity requires an externally protected secret; SHA-256 alone is not authentication",
        ],"runs": runs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "schema":report["schema"],"seeds":list(seeds),
        "source_records":len(records),"source_sha256":report["source_sha256"],
        "results":[{"accepted":r["accepted"],"retained":r["working_shelf_records"],
                    "ratio":r["independent_holdout"]["ratio"],
                    "recall":r["relevance"]["mean_recall"],
                    "recipe":r["selected_recipe"],"trials":r["candidate_count"]}
                   for r in runs],
        "report":str(args.output)},indent=2))
    return 0 if all(run["accepted"] for run in runs) else 2


if __name__ == "__main__":
    raise SystemExit(main())
