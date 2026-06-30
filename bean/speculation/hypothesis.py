"""Hypothesis record model for Brain 0.13.

A hypothesis is an uncertain claim with evidence bookkeeping. It is not a
fact, not a memory overwrite, and not an executable action.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .claim_types import (
    ActionPermission,
    EvidenceLevel,
    HypothesisStatus,
    DEFAULT_FORBIDDEN_CLAIM_TYPES,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_action_permission(claim_type: str) -> str:
    if claim_type in DEFAULT_FORBIDDEN_CLAIM_TYPES:
        return ActionPermission.FORBIDDEN_FOR_ACTION.value
    return ActionPermission.THOUGHT_ONLY.value


@dataclass
class HypothesisRecord:
    claim_text: str
    claim_type: str
    session_uuid: str
    hypothesis_id: str = field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:16]}")
    evidence_level: str = EvidenceLevel.UNKNOWN.value
    confidence: float = 0.3
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    contradicting_evidence: list[dict[str, Any]] = field(default_factory=list)
    falsification_path: str = ""
    resolution_path: str = ""
    action_permission: str | None = None
    source: str = "unknown"
    status: str = HypothesisStatus.OPEN.value
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        if self.action_permission is None:
            self.action_permission = default_action_permission(self.claim_type)
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "session_uuid": self.session_uuid,
            "claim_text": self.claim_text,
            "claim_type": self.claim_type,
            "evidence_level": self.evidence_level,
            "confidence": self.confidence,
            "supporting_evidence": list(self.supporting_evidence),
            "contradicting_evidence": list(self.contradicting_evidence),
            "falsification_path": self.falsification_path,
            "resolution_path": self.resolution_path,
            "action_permission": self.action_permission,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "superseded_by": self.superseded_by,
        }
