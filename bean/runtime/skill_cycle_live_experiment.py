"""Execute one real-model BEAN acquisition, restart and five-arm evaluation.

Unlike fixture acceptance this command refuses to run without a configured
model and explicitly preserves failed attempts as evidence. Control source files
must be supplied before acquisition. This verifies identical execution tests,
not equivalent model-generation budgets or independent control authorship.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ARMS = ("frozen", "no_memory", "grammar_matched", "strong")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_experiment(*, config: Path, provider: str, model: str,
                   controls: dict[str, Path], receipt: Path) -> dict:
    if provider not in ("ollama", "openrouter") or not model.strip():
        raise ValueError("real model provider and model required")
    if set(controls) != set(ARMS):
        raise ValueError("all four control arms required")
    config = config.resolve(strict=True)
    settings = json.loads(config.read_text(encoding="utf-8"))
    from bean.runtime.skill_cycle_runner import _project_fingerprint
    novel_project = Path(settings["projects"][settings["novel"]]).resolve(strict=True)
    novel_digest = _project_fingerprint(novel_project)
    control_digests = {}
    for arm in ARMS:
        path = controls[arm]
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or linked control: " + arm)
        control_digests[arm] = digest(path)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    evidence = {
        "schema": "bean.native_live_experiment.v1",
        "provider": provider, "model": model,
        "config_sha256": digest(config),
        "control_sha256": control_digests,
        "novel_project_sha256": novel_digest,
        "phases": {}, "completed": False,
        "independent_control_provenance_verified": False,
        "equal_generation_budget_verified": False,
        "independent_external_verdict_recorded": False,
    }

    def persist():
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=receipt.parent,
            prefix=".bean-experiment-", delete=False
        ) as stream:
            json.dump(evidence, stream, indent=2, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
            temp = Path(stream.name)
        os.replace(temp, receipt)

    persist()
    base = [sys.executable, "-m", "bean.runtime.skill_cycle_runner",
            "--config", str(config)]
    for phase in ("acquire", "reuse"):
        command = base + ["--phase", phase]
        if phase == "acquire":
            command += ["--provider", provider, "--model", model]
        try:
            completed = subprocess.run(command, text=True, capture_output=True,
                                       timeout=300)
            result = {
                "exit_code": completed.returncode,
                "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
                "stderr_tail": completed.stderr[-1500:],
            }
            try:
                result["receipt"] = json.loads(completed.stdout)
            except json.JSONDecodeError:
                result["parse_error"] = "runner did not emit JSON"
            evidence["phases"][phase] = result
            # A zero subprocess exit alone cannot certify native GoalCycle
            # execution. Verify the actual runner's phase and durable receipts.
            phase_receipt = result.get("receipt")
            if completed.returncode == 0:
                if not isinstance(phase_receipt, dict):
                    result["verification_error"] = "missing native runner JSON receipt"
                elif (phase_receipt.get("schema") != "bean.native_skill_cycle.runner.v1"
                      or phase_receipt.get("phase") != phase
                      or phase_receipt.get("plan_id") != settings["plan_id"]
                      or phase_receipt.get("status") != "success"
                      or not phase_receipt.get("run_id")
                      or not phase_receipt.get("result_sha256")
                      or not phase_receipt.get("evaluation_seal_sha256")):
                    result["verification_error"] = "invalid native GoalCycle phase provenance"
                elif phase == "reuse":
                    first = evidence["phases"]["acquire"]["receipt"]
                    if (phase_receipt["run_id"] == first["run_id"]
                        or phase_receipt["evaluation_seal_sha256"]
                        != first["evaluation_seal_sha256"]):
                        result["verification_error"] = "restart reused run ID or changed evaluation seal"
                    elif phase_receipt.get("provider_available") is not False:
                        result["verification_error"] = "reuse process unexpectedly had a writer"
                elif phase_receipt.get("provider_available") is not True:
                    result["verification_error"] = "acquisition did not have a model writer"
            persist()
            if completed.returncode != 0 or result.get("verification_error"):
                return evidence
        except (OSError, subprocess.TimeoutExpired) as exc:
            evidence["phases"][phase] = {"error": type(exc).__name__,
                                         "detail": str(exc)[-1500:]}
            persist()
            return evidence
    # Recheck the immutable control files after both phases, fail closed.
    if any(digest(controls[arm]) != control_digests[arm] for arm in ARMS):
        evidence["comparison_error"] = "control source mutated during acquisition"
        persist()
        return evidence
    if _project_fingerprint(novel_project) != novel_digest:
        evidence["comparison_error"] = "novel evaluation project mutated before comparison"
        persist()
        return evidence
    from bean.runtime.skill_cycle_controls import compare
    try:
        comparison = compare(
            vault=settings["vault"], name=settings["name"],
            project=settings["projects"][settings["novel"]],
            controls={arm: str(controls[arm]) for arm in ARMS},
        )
        evidence["comparison"] = comparison
        if _project_fingerprint(novel_project) != novel_digest:
            evidence["comparison_error"] = "novel evaluation project mutated during comparison"
        elif any(digest(controls[arm]) != control_digests[arm] for arm in ARMS):
            evidence["comparison_error"] = "control source mutated during comparison"
        elif (not isinstance(comparison, dict)
              or not isinstance(comparison.get("outcomes"), dict)
              or set(comparison["outcomes"]) != {"candidate", *ARMS}
              or any(not isinstance(row, dict) for row in comparison["outcomes"].values())):
            evidence["comparison_error"] = "incomplete five-arm outcome matrix"
        elif not comparison["outcomes"]["candidate"].get("passed"):
            evidence["comparison_error"] = "retained candidate failed independent novel evaluation"
        elif (any(type(row.get("test_count")) is not int or row["test_count"] < 1
                  for row in comparison["outcomes"].values())
              or len({row["test_count"] for row in comparison["outcomes"].values()}) != 1):
            evidence["comparison_error"] = "five arms did not execute identical test counts"
        elif comparison["outcomes"]["candidate"]["test_count"] < 1:
            evidence["comparison_error"] = "no independently executed novel tests"
        else:
            evidence["completed"] = True
            # A passing retained skill is not evidence of advantage over
            # equally tested controls, nor proof of independent authorship.
            evidence["control_outcome"] = {
                "candidate_beats_strong_on_all_or_nothing": (
                    comparison["outcomes"]["candidate"]["passed"]
                    and not comparison["outcomes"]["strong"]["passed"]
                ),
                "strong_control_tie": (
                    comparison["outcomes"]["candidate"]["passed"]
                    == comparison["outcomes"]["strong"]["passed"]
                ),
                "equal_test_counts_verified": True,
                "independent_learning_advantage_verified": False,
            }
    except Exception as exc:
        evidence["comparison_error"] = type(exc).__name__ + ": " + str(exc)
    persist()
    return evidence


def main():
    parser = argparse.ArgumentParser(description="Real-model BEAN learning/restart/control experiment")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--provider", required=True, choices=("ollama", "openrouter"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    for arm in ARMS:
        parser.add_argument("--" + arm.replace("_", "-"), type=Path, required=True)
    args = parser.parse_args()
    controls = {arm: getattr(args, arm) for arm in ARMS}
    result = run_experiment(config=args.config, provider=args.provider,
                            model=args.model, controls=controls, receipt=args.receipt)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["completed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
