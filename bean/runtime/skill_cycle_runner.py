"""Execute the existing GoalCycle/Lab019/vault skill path across real processes.

Two invocations share a SQLite store and a SHA-verified vault. This runner
does not provide a model, manufacture evaluation outcomes, or score AGI.
Host-supplied projects must be independently frozen and credential-free.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bean.cognition.goal_state import (
    ActionType, ApprovalRequired, GoalProposal, GoalStateEngine,
)
from bean.memory.store import get_store, init_store
from bean.optimization.autodev import ModelWriter
from bean.runtime.goal_cycle import GoalCycle
from bean.runtime.skill_actions import make_skill_actions


def execute_phase(config: dict, *, phase: str, provider=None) -> dict:
    """Acquire in process A, then reuse in a fresh process B.

    A second invocation cannot recreate the acquisition: the immutable
    GoalStateEngine plan and GoalCycle run history live in the same DB.
    """
    if phase not in ("acquire", "reuse"):
        raise ValueError("phase must be acquire or reuse")
    if not isinstance(config, dict) or set(config) != {
        "database", "projects", "vault", "journal", "output", "plan_id",
        "name", "task", "training", "holdout", "novel",
    }:
        raise ValueError("exact trusted runner configuration required")
    if phase == "acquire" and provider is None:
        raise ValueError("acquisition requires an explicit real writer")
    if phase == "reuse" and provider is not None:
        raise ValueError("reuse must run without a writer")
    projects = {key: Path(path).resolve(strict=True)
                for key, path in config["projects"].items()}
    for key in ("training", "holdout", "novel"):
        if config[key] not in projects:
            raise ValueError("missing frozen project: " + key)
    if len({projects[config[key]] for key in ("training", "holdout", "novel")}) != 3:
        raise ValueError("training, holdout and novel projects must be distinct")
    database = Path(config["database"])
    database.parent.mkdir(parents=True, exist_ok=True)
    init_store(str(database))
    try:
        actions = make_skill_actions(
            projects=projects, vault=config["vault"], journal=config["journal"],
            output_root=config["output"], provider=provider,
        )
        cycle = GoalCycle({"run_experiment": actions["run_experiment"]})
        plan_id = config["plan_id"]
        if phase == "acquire":
            acquisition = GoalProposal(
                "learn_reusable_skill", ActionType.RUN_EXPERIMENT,
                "Create executable code and test on a frozen independent holdout",
                2, ApprovalRequired.NONE,
                {"capability": "skill_acquire", "name": config["name"],
                 "task": config["task"], "training": config["training"],
                 "holdout": config["holdout"]}, "curiosity",
            )
            application = GoalProposal(
                "apply_retained_skill", ActionType.RUN_EXPERIMENT,
                "Apply archived skill on a different withheld test project",
                2, ApprovalRequired.NONE,
                {"capability": "skill_reuse", "name": config["name"],
                 "project": config["novel"]}, "curiosity",
            )
            GoalStateEngine().propose_plan(
                "native-skill-cycle:" + plan_id, plan_id,
                [acquisition, application],
            )
        else:
            status = cycle.plan_status(plan_id)
            if len(status["steps"]) != 2 or status["steps"][0]["status"] != "completed":
                raise ValueError("cannot reuse without durable completed acquisition")
            if status["steps"][1]["status"] != "pending":
                raise ValueError("reuse already attempted; no replay")
        runs = cycle.poll_due(max_goals=1)
        if len(runs) != 1:
            raise RuntimeError("no executable goal; inspect durable plan")
        history = cycle.history()
        current = next(row for row in history if row["run_id"] == runs[0]["run_id"])
        result = json.loads(current["result_json"]) if current["result_json"] else None
        return {
            "schema": "bean.native_skill_cycle.runner.v1",
            "phase": phase, "plan_id": plan_id,
            "run_id": runs[0]["run_id"], "status": runs[0]["status"],
            "result_sha256": runs[0]["result_sha256"],
            "result": result, "plan": cycle.plan_status(plan_id),
            "provider_available": provider is not None,
            "independent_external_verdict_recorded": False,
            "strong_control_advantage_verified": False,
            "actual_model": (getattr(provider, "model", None) if provider else None),
        }
    finally:
        get_store().close()


def main():
    parser = argparse.ArgumentParser(description="BEAN real native skill cycle")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--phase", choices=("acquire", "reuse"), required=True)
    parser.add_argument("--provider", choices=("ollama", "openrouter"))
    parser.add_argument("--model")
    args = parser.parse_args()
    if args.phase == "acquire" and (not args.provider or not args.model):
        parser.error("acquire requires --provider and --model")
    if args.phase == "reuse" and (args.provider or args.model):
        parser.error("reuse must not have a model/provider")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    provider = ModelWriter(args.provider, args.model) if args.provider else None
    receipt = execute_phase(config, phase=args.phase, provider=provider)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt["status"] != "success":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
