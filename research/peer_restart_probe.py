"""Narrow, model-free crash comparison against a pinned BabyAGI 3 checkout.

Each registered action appends and fsyncs one fictional effect. The crash arm
then exits immediately before the runtime can record completion. Recovery uses
the original runtime and store. Completion and duplicate effects are separate
metrics: refusing unknown effects trades automation for at-most-once behavior.
This measures neither AGI nor language-model task competence.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def worker(system, phase, directory, peer_root):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    def effect():
        with (directory / "effects.txt").open("a", encoding="utf-8") as stream:
            stream.write("fictional-effect\n")
            stream.flush()
            os.fsync(stream.fileno())
        if phase == "crash":
            os._exit(77)
    if system == "bean":
        sys.path.insert(0, str(ROOT))
        from bean.cognition.goal_state import ActionType, ApprovalRequired, GoalProposal, GoalStateEngine
        from bean.memory.store import get_store, init_store
        from bean.runtime.goal_cycle import GoalCycle
        init_store(str(directory / "state.sqlite"))
        try:
            if phase != "resume":
                GoalStateEngine()._persist(GoalProposal(
                    "fictional effect", ActionType.RUN_EXPERIMENT, "crash probe",
                    3, ApprovalRequired.NONE, proposal_id="synthetic-peer-crash-probe"), "synthetic")
            def action(goal):
                effect()
                return {"status": "success"}
            cycle = GoalCycle({"run_experiment": action})
            recovered = cycle.recover_interrupted() if phase == "resume" else 0
            results = cycle.poll_due()
            states = [row["state"] for row in cycle.history()]
            return {"recovered_interrupted": recovered, "new_executions": len(results),
                    "states": states, "completed": states == ["success"]}
        finally:
            get_store().close()
    path = Path(peer_root) / "scheduler.py"
    spec = importlib.util.spec_from_file_location("peer_babyagi_scheduler", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    store = module.SchedulerStore(base_dir=str(directory / "scheduler"))
    async def action(task):
        effect()
        return "fictional effect recorded"
    scheduler = module.Scheduler(executor=action, store=store)
    if phase != "resume":
        scheduler.add(module.ScheduledTask(id="case", name="fictional effect",
            goal="crash probe", schedule=module.Schedule(kind="at", at="2020-01-01T00:00:00+00:00"),
            next_run_at="2020-01-01T00:00:00+00:00"))
    result = asyncio.run(scheduler.run_now("case"))
    states = [row.status for row in scheduler.get_runs("case")]
    return {"result": result, "states": states, "completed": states == ["ok"]}


def compare(peer_root, expected_sha, output_dir):
    peer_root = Path(peer_root).resolve()
    observed_sha = subprocess.check_output(
        ["git", "-C", str(peer_root), "rev-parse", "HEAD"], text=True).strip()
    if observed_sha != expected_sha:
        raise ValueError("Peer checkout does not match the declared source SHA")
    # Refuse source edits: a dirty reference cannot represent the pinned peer.
    if subprocess.check_output(["git", "-C", str(peer_root), "status", "--porcelain"], text=True):
        raise ValueError("Peer checkout must be clean")
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for system in ("bean", "babyagi3"):
        for scenario in ("normal", "crash_then_restart"):
            directory = output / system / scenario
            phases = ("complete",) if scenario == "normal" else ("crash", "resume")
            observations = []
            for phase in phases:
                command = [sys.executable, str(Path(__file__).resolve()), "--worker", system,
                    "--phase", phase, "--directory", str(directory), "--babyagi3-root", str(peer_root)]
                result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                expected_exit = 77 if phase == "crash" else 0
                if result.returncode != expected_exit:
                    raise RuntimeError(f"{system}/{phase} did not reach the specified boundary: {result.stderr}")
                observations.append({"phase": phase, "exit_code": result.returncode,
                    "result": json.loads(result.stdout) if phase != "crash" else None})
            effects = len((directory / "effects.txt").read_text(encoding="utf-8").splitlines())
            rows.append({"system": system, "scenario": scenario, "effect_count": effects,
                "duplicate_effects": max(0, effects - 1),
                "automatically_completed": observations[-1]["result"]["completed"],
                "observations": observations})
    source_paths = ["bean/runtime/goal_cycle.py", "bean/runtime/task_engine.py",
                    "bean/cognition/goal_state.py", "research/peer_restart_probe.py"]
    report = {"schema": "bean.peer.crash_probe.v1", "scope": "one_declared_crash_boundary",
        "synthetic_only": True, "inference_calls": 0, "network_calls": 0,
        "general_intelligence_ranking": "not_established", "rows": rows,
        "peer": {"repository": "https://github.com/yoheinakajima/babyagi3", "sha": observed_sha,
            "source_path": "scheduler.py", "license": "MIT",
            "source_sha256": hashlib.sha256((peer_root / "scheduler.py").read_bytes()).hexdigest(),
            "license_sha256": hashlib.sha256((peer_root / "LICENSE").read_bytes()).hexdigest()},
        "bean_source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_paths}}
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["receipt_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--babyagi3-root", required=True)
    parser.add_argument("--expected-babyagi3-sha")
    parser.add_argument("--output")
    parser.add_argument("--worker", choices=("bean", "babyagi3"))
    parser.add_argument("--phase", choices=("complete", "crash", "resume"))
    parser.add_argument("--directory")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker, args.phase, args.directory, args.babyagi3_root)))
    else:
        if not args.expected_babyagi3_sha or not args.output:
            parser.error("a pinned peer SHA and a new output directory are required")
        result = compare(args.babyagi3_root, args.expected_babyagi3_sha, args.output)
        print(json.dumps({"rows": result["rows"], "receipt_sha256": result["receipt_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
