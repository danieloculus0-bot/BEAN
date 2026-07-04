"""Discipline checks for Brain 0.13."""

from .claim_types import CERTAINTY_PHRASES, GROUNDED_EVIDENCE_LEVELS, NON_FACTUAL_CLAIM_TYPES, VALID_ACTION_PERMISSIONS, VALID_CLAIM_TYPES, VALID_EVIDENCE_LEVELS

BLOCKED_IDENTITY_PHRASES = ["i am alive", "i am a person", "i am self-aware", "i have feelings", "i love"]


def check_speculation_not_fact(claim_type: str, evidence_level: str) -> tuple[bool, str]:
    if claim_type in ("observation", "memory") and evidence_level not in GROUNDED_EVIDENCE_LEVELS:
        return False, "factual claim requires grounded evidence"
    if claim_type in NON_FACTUAL_CLAIM_TYPES and evidence_level == "observed":
        return False, "non-factual claim cannot be marked observed"
    return True, "ok"


def run_full_discipline_check(text: str, claim_type: str, evidence_level: str, action_permission: str) -> dict:
    failures = []
    if claim_type not in VALID_CLAIM_TYPES: failures.append("invalid claim_type")
    if evidence_level not in VALID_EVIDENCE_LEVELS: failures.append("invalid evidence_level")
    if action_permission not in VALID_ACTION_PERMISSIONS: failures.append("invalid action_permission")
    ok, reason = check_speculation_not_fact(claim_type, evidence_level)
    if not ok: failures.append(reason)
    low = (text or "").lower()
    if claim_type in NON_FACTUAL_CLAIM_TYPES and evidence_level not in GROUNDED_EVIDENCE_LEVELS:
        if any(p in low for p in CERTAINTY_PHRASES): failures.append("certainty language without evidence")
    if any(p in low for p in BLOCKED_IDENTITY_PHRASES): failures.append("unsupported identity language")
    return {"valid": not failures, "failures": failures}
