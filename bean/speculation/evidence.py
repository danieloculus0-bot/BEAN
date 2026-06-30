"""Evidence links for speculative hypotheses.

Evidence must point at something explicit. Manual evidence is allowed, but it
must say it is manual instead of pretending a source row exists.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

VALID_EVIDENCE_SOURCE_TYPES = {
    "bean_event",
    "reasoning_proposal",
    "manual",
    "memory_record",
    "world_claim",
    "sensor_record",
}

VALID_EVIDENCE_POLARITIES = {"supporting", "contradicting"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvidenceLink:
    hypothesis_id: str
    source_type: str
    polarity: str
    note: str
    source_id: str | None = None
    link_id: str = field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:16]}")
    created_at: str = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        if self.source_type not in VALID_EVIDENCE_SOURCE_TYPES:
            raise ValueError(f"Invalid source_type: {self.source_type!r}")
        if self.polarity not in VALID_EVIDENCE_POLARITIES:
            raise ValueError(f"Invalid polarity: {self.polarity!r}")
        if self.source_type != "manual" and not self.source_id:
            raise ValueError("source_id is required for non-manual evidence")

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "hypothesis_id": self.hypothesis_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "polarity": self.polarity,
            "note": self.note,
            "created_at": self.created_at,
        }
