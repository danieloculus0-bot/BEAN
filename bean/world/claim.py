"""
bean/world/claim.py

Atomic structured belief record for BEAN's self/world model.
Claims are evidence-bearing, confidence-tracked, and supersedable.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class ClaimCategory(str, Enum):
    SELF = "self"
    ENVIRONMENT = "environment"
    RELATIONAL = "relational"
    TEMPORAL = "temporal"
    UNCERTAINTY = "uncertainty"


class ClaimSource(str, Enum):
    EVENT_LOG = "event_log"
    REFLECTION = "reflection"
    SUPERVISOR = "supervisor"
    INFERENCE = "inference"
    BOOTSTRAP = "bootstrap"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


@dataclass
class Claim:
    key: str
    content: str
    category: ClaimCategory
    source_type: ClaimSource
    confidence: float
    claim_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    value: Optional[str] = None
    source_ref: Optional[str] = None
    evidence: list[str] = field(default_factory=list)
    active: bool = True
    superseded_by: Optional[str] = None
    notes: str = ""
    created_at: str = field(default_factory=_now)

    def __post_init__(self):
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        if not isinstance(self.category, ClaimCategory):
            self.category = ClaimCategory(self.category)
        if not isinstance(self.source_type, ClaimSource):
            self.source_type = ClaimSource(self.source_type)

    def parsed_value(self, default=None):
        if self.value is None:
            return default
        try:
            return json.loads(self.value)
        except Exception:
            return self.value

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "key": self.key,
            "content": self.content,
            "category": self.category.value,
            "source_type": self.source_type.value,
            "confidence": self.confidence,
            "value": self.value,
            "source_ref": self.source_ref,
            "evidence": self.evidence,
            "active": self.active,
            "superseded_by": self.superseded_by,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row) -> "Claim":
        return cls(
            claim_id=row["claim_id"],
            key=row["key"],
            content=row["content"],
            category=ClaimCategory(row["category"]),
            source_type=ClaimSource(row["source_type"]),
            confidence=row["confidence"],
            value=row["value"],
            source_ref=row["source_ref"],
            evidence=json.loads(row["evidence"] or "[]"),
            active=bool(row["active"]),
            superseded_by=row["superseded_by"],
            notes=row["notes"] or "",
            created_at=row["created_at"],
        )


def make_claim(
    key: str,
    content: str,
    category: ClaimCategory,
    source_type: ClaimSource,
    confidence: float,
    value: Any = None,
    source_ref: Optional[str] = None,
    evidence: Optional[list[str]] = None,
    notes: str = "",
) -> Claim:
    return Claim(
        key=key,
        content=content,
        category=category,
        source_type=source_type,
        confidence=confidence,
        value=_json_value(value),
        source_ref=source_ref,
        evidence=evidence or [],
        notes=notes,
    )
