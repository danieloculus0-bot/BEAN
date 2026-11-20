"""Register Lab019 skill acquisition and retained reuse as native BEAN GoalCycle actions.

Trusted host supplies immutable project IDs and a provider. Goals cannot select
arbitrary filesystem paths, shell commands, providers, or physical effectors.
The incubator's tests execute in disposable projects, not an OS sandbox.
"""
from __future__ import annotations

from pathlib import Path

from ..optimization.skill_incubator import NAME, incubate_skill
from ..optimization.skill_vault import promote, reuse, retrieve


def make_skill_actions(*, projects, vault, journal, output_root, provider,
                       attempts=5):
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
        if set(detail) != expected or not isinstance(detail["name"], str) or not NAME.fullmatch(detail["name"]):
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

    return {"skill_acquire": acquire, "skill_reuse": execute_retained}
