"""Register Lab019 skill acquisition and retained reuse as native BEAN GoalCycle actions.

Trusted host supplies immutable project IDs and a provider. Goals cannot select
arbitrary filesystem paths, shell commands, providers, or physical effectors.
The incubator's tests execute in disposable projects, not an OS sandbox.
"""
from __future__ import annotations

from pathlib import Path

from ..cognition.goal_state import goal_plan
from ..optimization.skill_incubator import NAME, incubate_skill
from ..optimization.skill_vault import promote, reuse, retrieve


def make_skill_actions(*, projects, vault, journal, output_root, provider,
                       attempts=5, fallback=None):
    """Return two registered GoalCycle actions using host-owned project mappings.

    Project IDs refer to directories selected by the host. Distinct holdout and
    reuse projects are required. A persisted skill is reusable after restart
    by recreating this registry against the same vault.
    """
    if not isinstance(projects, dict) or not projects:
        raise ValueError("host projects required")
    if any(not isinstance(k, str) or not NAME.fullmatch(k) for k in projects):
        raise ValueError("invalid host project ID")
    if len(set(str(Path(p).resolve(strict=True)) for p in projects.values())) != len(projects):
        raise ValueError("project directories must be distinct")
    if type(attempts) is not int or not 1 <= attempts <= 10:
        raise ValueError("attempts must be 1..10")
    if fallback is not None and not callable(fallback):
        raise ValueError("fallback must be a trusted registered action")
    paths = {key: Path(value).resolve(strict=True) for key, value in projects.items()}
    vault = Path(vault)
    journal = Path(journal)
    output_root = Path(output_root)

    def fields(goal, operation):
        detail = goal.get("action_detail")
        if not isinstance(detail, dict) or detail.get("capability") != operation:
            return None
        if operation == "skill_acquire":
            expected = {"capability", "name", "task", "training", "holdout"}
        else:
            expected = {"capability", "name", "project"}
        # GoalStateEngine.propose_plan injects this reserved metadata into
        # action_detail. Validate its immutable proposal identity rather than
        # rejecting every native ordered plan as an invalid skill request.
        if set(detail) - {"goal_plan"} != expected:
            return None
        if "goal_plan" in detail:
            try:
                goal_plan(detail, goal.get("proposal_id"))
            except (TypeError, ValueError):
                return None
        if not isinstance(detail["name"], str) or not NAME.fullmatch(detail["name"]):
            return None
        keys = ("training", "holdout") if operation == "skill_acquire" else ("project",)
        if any(not isinstance(detail[k], str) or detail[k] not in paths for k in keys):
            return None
        if operation == "skill_acquire":
            task = detail["task"]
            if (not isinstance(task, str) or not 12 <= len(task.strip()) <= 4000
                    or detail["training"] == detail["holdout"]):
                return None
        return detail

    def acquire(goal):
        detail = fields(goal, "skill_acquire")
        if detail is None:
            return {"status": "unknown", "reason": "invalid_skill_goal"}
        name = detail["name"]
        # Never overwrite existing skill or accept a repeated goal as new learning.
        try:
            retrieve(vault=vault, name=name)
        except FileNotFoundError:
            pass
        else:
            return {"status": "n/a", "reason": "skill_already_promoted"}
        output = output_root / name
        if output.exists() or output.is_symlink():
            return {"status": "unknown", "reason": "existing_incubation_output"}
        report = incubate_skill(
            project=paths[detail["training"]], name=name, task=detail["task"],
            journal_path=journal, output=output, provider=provider,
            attempts=attempts, holdout_project=paths[detail["holdout"]])
        if not report.get("skill_promotion_ready"):
            return {"status": "failed", "reason": "independent_holdout_not_passed",
                    "model_generated": report.get("skill_origin"),
                    "attempts": report.get("attempts")}
        receipt = promote(report=report, output=output, journal_path=journal, vault=vault)
        return {"status": "success", "skill": name,
                "source_sha256": receipt["source_sha256"],
                "promotion_receipt_sha256": receipt["receipt_sha256"],
                "provider_used": True, "independent_holdout_verified": True,
                "restart_reuse_verified": False}

    def execute_retained(goal):
        detail = fields(goal, "skill_reuse")
        if detail is None:
            return {"status": "unknown", "reason": "invalid_reuse_goal"}
        try:
            result = reuse(vault=vault, name=detail["name"], project=paths[detail["project"]])
        except (FileNotFoundError, ValueError, KeyError) as exc:
            return {"status": "failed", "reason": type(exc).__name__}
        # A training or promotion-holdout replay is not independent transfer.
        passed = result["passed"] and result["independent_from_promotion_holdout"]
        return {"status": "success" if passed else "failed",
                "skill": detail["name"], "passed": result["passed"],
                "new_test_set": result["independent_from_promotion_holdout"],
                "source_sha256": result["source_sha256"],
                "reuse_tests_sha256": result["reuse_tests_sha256"],
                "provider_invoked": False}

    def run_experiment(goal):
        """Bridge the existing ActionType.RUN_EXPERIMENT to skill actions.

        GoalCycle stores ActionType.RUN_EXPERIMENT (not skill_acquire/reuse) in
        its canonical goal table. Existing experiment handlers can be passed
        as a trusted fallback, preserving other Core experiment capabilities.
        """
        detail = goal.get("action_detail") if isinstance(goal, dict) else None
        capability = detail.get("capability") if isinstance(detail, dict) else None
        if capability == "skill_acquire":
            return acquire(goal)
        if capability == "skill_reuse":
            return execute_retained(goal)
        return (fallback(goal) if fallback is not None else
                {"status": "unknown", "reason": "unsupported_experiment_capability"})

    return {"skill_acquire": acquire, "skill_reuse": execute_retained,
            "run_experiment": run_experiment}
