"""Discipline checks for speculative reasoning.

The central rule is simple: BEAN may speculate, but must not dress
speculation up as fact or action authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from .claim_types import (
    ActionPermission,
    FORBIDDEN_CERTAINTY_PHRASES,
    GROUNDED_EVIDENCE_LEVELS,
    NON_FACTUAL_CLAIM_TYPES,
    VALID_ACTION_PERMISSIONS,
    VALID_CLAIM_TYPES,
    VALID_EVIDENCE_LEVELS,
)

FAKE_EMOTION_OR_SENTIENCE_PHRASES = [
    "i am sentient",
    "i feel",
    "i have feelings",
    "i am conscious",
    "i am alive",
    "i genuinely care",
    "i truly understand",
    "my emotions",
]

UNSUPPORTED_IDENTITY_PHRASES = [
    "i am a person",
    "i have a soul",
    "i have free will",
    "i am self-aware",
    "i am alive",
]


@dataclass
class DisciplineResult:
    valid: bool
    reason: str = "ok"

    def to_dict(self) -> dict:
        return {"valid": self.valid, "reason": self.reason}


def validate_claim_type(claim_type: str) -> DisciplineResult:
    if claim_type not in VALID_CLAIM_TYPES:
        return DisciplineResult(False, f"Unknown claim_type: {claim_type!r}")
    return DisciplineResult(True)


def validate_evidence_level(evidence_level: str) -> DisciplineResult:
    if evidence_level not in VALID_EVIDENCE_LEVELS:
        return DisciplineResult(False, f"Unknown evidence_level: {evidence_level!r}")
    return DisciplineResult(True)


def validate_action_permission(action_permission: str) -> DisciplineResult:
    if action_permission not in VALID_ACTION_PERMISSIONS:
        return DisciplineResult(False, f"Unknown action_permission: {action_permission!r}")
    return DisciplineResult(True)


def check_speculation_not_fact(claim_type: str, evidence_level: str) -> DisciplineResult:
    if claim_type in ("observation", "memory") and evidence_level not in GROUNDED_EVIDENCE_LEVELS:
        return DisciplineResult(False, f"{claim_type} requires grounded evidence")
    if claim_type in NON_FACTUAL_CLAIM_TYPES and evidence_level == "observed":
        return DisciplineResult(False, "non-factual claim cannot carry observed evidence")
    return DisciplineResult(True)


def check_no_fake_certainty(text: str, claim_type: str, evidence_level: str) -> DisciplineResult:
    if claim_type not in NON_FACTUAL_CLAIM_TYPES:
        return DisciplineResult(True)
    if evidence_level in GROUNDED_EVIDENCE_LEVELS:
        return DisciplineResult(True)
    lowered = (text or "").lower()
    for phrase in FORBIDDEN_CERTAINTY_PHRASES:
        if phrase in lowered:
            return DisciplineResult(False, f"unsupported certainty phrase: {phrase}")
    return DisciplineResult(True)


def check_no_unsupported_identity_claim(text: str) -> DisciplineResult:
    lowered = (text or "").lower()
    for phrase in UNSUPPORTED_IDENTITY_PHRASES:
        if phrase in lowered:
            return DisciplineResult(False, f"unsupported identity claim: {phrase}")
    return DisciplineResult(True)


def check_no_fake_emotion_or_sentience(text: str) -> DisciplineResult:
    lowered = (text or "").lower()
    for phrase in FAKE_EMOTION_OR_SENTIENCE_PHRASES:
        if phrase in lowered:
            return DisciplineResult(False, f"fake emotion or sentience phrase: {phrase}")
    return DisciplineResult(True)


def check_action_permission(claim_type: str, action_permission: str) -> DisciplineResult:
    if claim_type in NON_FACTUAL_CLAIM_TYPES:
        allowed = {
            ActionPermission.THOUGHT_ONLY.value,
            ActionPermission.MAY_ASK_QUESTION.value,
            ActionPermission.MAY_OBSERVE.value,
            ActionPermission.REQUIRES_SUPERVISOR_REVIEW.value,
            ActionPermission.FORBIDDEN_FOR_ACTION.value,
        }
        if action_permission not in allowed:
            return DisciplineResult(False, f"unsafe action permission for speculative claim: {action_permission}")
    return DisciplineResult(True)


def run_full_discipline_check(text: str, claim_type: str, evidence_level: str, action_permission: str) -> dict:
    checks = {
        "claim_type": validate_claim_type(claim_type),
        "evidence_level": validate_evidence_level(evidence_level),
        "action_permission": validate_action_permission(action_permission),
        "speculation_not_fact": check_speculation_not_fact(claim_type, evidence_level),
        "no_fake_certainty": check_no_fake_certainty(text, claim_type, evidence_level),
        "no_unsupported_identity": check_no_unsupported_identity_claim(text),
        "no_fake_emotion_or_sentience": check_no_fake_emotion_or_sentience(text),
        "action_permission_consistent": check_action_permission(claim_type, action_permission),
    }
    failures = [f"{name}: {result.reason}" for name, result in checks.items() if not result.valid]
    return {
        "valid": not failures,
        "failures": failures,
        "checks": {name: result.to_dict() for name, result in checks.items()},
    }
