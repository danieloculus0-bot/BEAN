"""Verify a real model-produced source artifact in a different, secret-free job."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from bean.optimization.autodev import evaluate

TARGET = "bean/skills/clip_score.py"


def verify(*, artifact: Path, project: Path, output: Path) -> dict:
    artifact = Path(artifact)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    receipt = json.loads((artifact / "receipt.json").read_text(encoding="utf-8"))
    result = {
        "schema": "bean.openrouter.free.validation.v1",
        "model_requested": receipt["model_requested"],
        "model_served": receipt.get("model_served"),
        "provider_status": receipt["provider_status"],
        "verdict": "not_tested",
        "test_count": 0,
        "baseline_failed": None,
        "reason": receipt.get("reason"),
    }
    if receipt["model_requested"] != "openrouter/free":
        raise ValueError("free-only model contract violated")
    if receipt["provider_status"] == "proposal_generated":
        candidate_path = artifact / "proposal.py"
        data = candidate_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != receipt["generated_source_sha256"]:
            raise ValueError("model candidate hash mismatch")
        baseline = evaluate(project, TARGET, (project / TARGET).read_text(encoding="utf-8"))
        candidate = evaluate(project, TARGET, data.decode("utf-8"))
        result["baseline_failed"] = not baseline["passed"]
        result["test_count"] = candidate["test_count"]
        result["verdict"] = ("model_trial_passed" if not baseline["passed"]
                             and candidate["passed"] and candidate["test_count"] >= 7
                             else "model_trial_failed")
        result["test_excerpt"] = candidate["excerpt"][-600:]
    (output / "verified-result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(artifact=args.artifact, project=args.project, output=args.output),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
