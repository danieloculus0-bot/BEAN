"""Validation for reasoning action candidates.

This module deliberately validates proposal records only. It does not import
hardware drivers and does not execute motion.
"""

from __future__ import annotations

from typing import Any

VALID_ACTION_TYPES = {
    "ask_clarification",
    "propose_observation",
    "propose_repair",
    "propose_motion",
    "record_hypothesis",
    "defer",
}

VALID_RISK_LEVELS = {"low", "medium", "high", "blocked"}


def validate_action_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(candidate, dict):
        return {"valid": False, "errors": ["candidate must be an object"], "candidate": candidate}
    action_type = candidate.get("action_type")
    if action_type not in VALID_ACTION_TYPES:
        errors.append(f"unknown action_type: {action_type!r}")
    risk_level = candidate.get("risk_level", "medium")
    if risk_level not in VALID_RISK_LEVELS:
        errors.append(f"unknown risk_level: {risk_level!r}")
    rationale = str(candidate.get("rationale", ""))
    if not rationale:
        errors.append("rationale required")
    if action_type == "propose_motion":
        errors.append("motion candidates cannot be validated for execution by reasoning")
        candidate = dict(candidate)
        candidate["status"] = "requires_supervisor_review"
        candidate["motion_enabled"] = False
    if candidate.get("execute") is True or candidate.get("execute_now") is True:
        errors.append("reasoning candidates may not request execution")
    return {"valid": not errors, "errors": errors, "candidate": candidate}


def validate_all_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for candidate in candidates or []:
        result = validate_action_candidate(candidate)
        if result["valid"]:
            valid.append(result["candidate"])
        else:
            rejected.append(result)
    return valid, rejected
