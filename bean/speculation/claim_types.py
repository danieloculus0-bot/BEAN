"""Canonical vocabulary for BEAN speculative reasoning.

Brain 0.13 keeps uncertain claims labeled as uncertain. These enums are
intentionally boring and explicit so providers, stores, tests, and runtime
commands cannot invent new categories casually.
"""

from __future__ import annotations

from enum import Enum


class ClaimType(str, Enum):
    OBSERVATION = "observation"
    MEMORY = "memory"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    SPECULATION = "speculation"
    COUNTERFACTUAL = "counterfactual"
    PREDICTION = "prediction"
    UNKNOWN = "unknown"


class EvidenceLevel(str, Enum):
    OBSERVED = "observed"
    STRONGLY_SUPPORTED = "strongly_supported"
    SUPPORTED = "supported"
    WEAKLY_SUPPORTED = "weakly_supported"
    SPECULATIVE = "speculative"
    HYPOTHETICAL = "hypothetical"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


class ActionPermission(str, Enum):
    THOUGHT_ONLY = "thought_only"
    MAY_ASK_QUESTION = "may_ask_question"
    MAY_OBSERVE = "may_observe"
    MAY_RECOMMEND = "may_recommend"
    REQUIRES_SUPERVISOR_REVIEW = "requires_supervisor_review"
    FORBIDDEN_FOR_ACTION = "forbidden_for_action"


class HypothesisStatus(str, Enum):
    OPEN = "open"
    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    CONTRADICTED = "contradicted"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


VALID_CLAIM_TYPES = {item.value for item in ClaimType}
VALID_EVIDENCE_LEVELS = {item.value for item in EvidenceLevel}
VALID_ACTION_PERMISSIONS = {item.value for item in ActionPermission}
VALID_HYPOTHESIS_STATUSES = {item.value for item in HypothesisStatus}

NON_FACTUAL_CLAIM_TYPES = {
    ClaimType.INFERENCE.value,
    ClaimType.HYPOTHESIS.value,
    ClaimType.SPECULATION.value,
    ClaimType.COUNTERFACTUAL.value,
    ClaimType.PREDICTION.value,
    ClaimType.UNKNOWN.value,
}

DEFAULT_FORBIDDEN_CLAIM_TYPES = {
    ClaimType.HYPOTHESIS.value,
    ClaimType.SPECULATION.value,
    ClaimType.COUNTERFACTUAL.value,
    ClaimType.PREDICTION.value,
    ClaimType.UNKNOWN.value,
}

GROUNDED_EVIDENCE_LEVELS = {
    EvidenceLevel.OBSERVED.value,
    EvidenceLevel.STRONGLY_SUPPORTED.value,
    EvidenceLevel.SUPPORTED.value,
}

UNSUPPORTED_EVIDENCE_LEVELS = {
    EvidenceLevel.WEAKLY_SUPPORTED.value,
    EvidenceLevel.SPECULATIVE.value,
    EvidenceLevel.HYPOTHETICAL.value,
    EvidenceLevel.UNKNOWN.value,
    EvidenceLevel.CONTRADICTED.value,
}

FORBIDDEN_CERTAINTY_PHRASES = [
    "definitely",
    "certainly",
    "proven",
    "guaranteed",
    "always",
    "never",
    "must be true",
    "i know this is true",
]
