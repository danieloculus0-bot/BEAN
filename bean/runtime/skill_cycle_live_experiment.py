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
            persist()
            if completed.returncode != 0:
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
    from bean.runtime.skill_cycle_controls import compare
    try:
        comparison = compare(
            vault=settings["vault"], name=settings["name"],
            project=settings["projects"][settings["novel"]],
            controls={arm: str(controls[arm]) for arm in ARMS},
        )
        evidence["comparison"] = comparison
        evidence["completed"] = True
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
