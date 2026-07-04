"""Hypothesis record for Brain 0.13."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .claim_types import DEFAULT_FORBIDDEN_CLAIM_TYPES


def default_action_permission(claim_type: str) -> str:
    return "forbidden_for_action" if claim_type in DEFAULT_FORBIDDEN_CLAIM_TYPES else "thought_only"


@dataclass
class HypothesisRecord:
    claim_text: str
    claim_type: str
    session_uuid: str
    hypothesis_id: str = field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:12]}")
    evidence_level: str = "unknown"
    confidence: float = 0.3
    supporting_evidence: list = field(default_factory=list)
    contradicting_evidence: list = field(default_factory=list)
    falsification_path: str = ""
    resolution_path: str = ""
    action_permission: str | None = None
    source: str = "unknown"
    status: str = "open"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    superseded_by: str | None = None

    def __post_init__(self):
        if self.action_permission is None:
            self.action_permission = default_action_permission(self.claim_type)
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    def to_dict(self) -> dict:
        return dict(self.__dict__)
