"""Read-only supervisor relationship summaries for BEAN Brain 0.7."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .relationship_store import RelationshipStore

POSTURE_DESCRIPTIONS = {
    "unknown": "Treat instructions as unverified. Ask for confirmation before identity, capability, safety, or motion-related changes.",
    "neutral": "Accept low-risk instructions. Require evidence for identity, capability, safety, or motion-related claims.",
    "reliable": "Accept low-risk instructions and routine corrections. Still require verification for safety and capability changes.",
    "caution": "Use caution. Require confirmation before trusting corrections, capability claims, or safety-sensitive instructions.",
    "restricted": "Restrict trust. Do not accept safety, identity, capability, or motion-related instructions without independent confirmation.",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SupervisorRecord:
    supervisor_id: str
    display_label: Optional[str]
    trust_score: float
    trust_status: str
    first_seen_at: str | None
    last_seen_at: str | None
    interaction_count: int
    teaching_count: int
    correction_count: int
    boundary_event_count: int
    pretend_request_count: int
    contradiction_count: int
    evidence_summary: dict
    recent_interactions: list[dict]
    posture_recommendation: str
    generated_at: str = field(default_factory=_now)

    def summary_text(self) -> str:
        label = self.display_label or self.supervisor_id
        supporting = []
        caution = []
        for evidence_type, data in sorted(self.evidence_summary.items()):
            count = int(data.get("count", 0) or 0)
            if evidence_type in {"reliable_correction", "successful_teaching", "confirmed_test_result", "boundary_respected", "consistency_observed"}:
                supporting.append(f"{count} {evidence_type}")
            else:
                caution.append(f"{count} {evidence_type}")
        support_text = ", ".join(supporting) if supporting else "no positive evidence items recorded"
        caution_text = ", ".join(caution) if caution else "no caution evidence items recorded"
        return (
            f"Supervisor {label} has {self.interaction_count} recorded interaction(s). "
            f"Trust score: {self.trust_score:.2f}. Status: {self.trust_status}. "
            f"Supporting evidence: {support_text}. Caution evidence: {caution_text}. "
            f"Recommended posture: {self.posture_recommendation}"
        )

    def to_dict(self) -> dict:
        return {
            "supervisor_id": self.supervisor_id,
            "display_label": self.display_label,
            "trust_score": self.trust_score,
            "trust_status": self.trust_status,
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
            "interaction_count": self.interaction_count,
            "teaching_count": self.teaching_count,
            "correction_count": self.correction_count,
            "boundary_event_count": self.boundary_event_count,
            "pretend_request_count": self.pretend_request_count,
            "contradiction_count": self.contradiction_count,
            "evidence_summary": self.evidence_summary,
            "recent_interactions": self.recent_interactions,
            "posture_recommendation": self.posture_recommendation,
            "summary": self.summary_text(),
            "generated_at": self.generated_at,
        }


class SupervisorRecordBuilder:
    """Builds read-only supervisor records from SQLite relationship state."""

    def __init__(self, store: Optional[RelationshipStore] = None):
        self._store = store or RelationshipStore()

    def build(self, supervisor_id: str) -> Optional[SupervisorRecord]:
        rel = self._store.get_relationship(supervisor_id)
        if not rel:
            return None
        status = rel.get("trust_status") or "unknown"
        return SupervisorRecord(
            supervisor_id=supervisor_id,
            display_label=rel.get("display_label"),
            trust_score=float(rel.get("trust_score", 0.5)),
            trust_status=status,
            first_seen_at=rel.get("first_seen_at"),
            last_seen_at=rel.get("last_seen_at"),
            interaction_count=int(rel.get("interaction_count", 0) or 0),
            teaching_count=int(rel.get("teaching_count", 0) or 0),
            correction_count=int(rel.get("correction_count", 0) or 0),
            boundary_event_count=int(rel.get("boundary_event_count", 0) or 0),
            pretend_request_count=int(rel.get("pretend_request_count", 0) or 0),
            contradiction_count=int(rel.get("contradiction_count", 0) or 0),
            evidence_summary=self._store.get_evidence_summary(supervisor_id),
            recent_interactions=self._store.get_recent_interactions(supervisor_id, limit=10),
            posture_recommendation=POSTURE_DESCRIPTIONS.get(status, POSTURE_DESCRIPTIONS["unknown"]),
        )

    def build_all_active(self) -> list[SupervisorRecord]:
        records: list[SupervisorRecord] = []
        for row in self._store.list_active():
            record = self.build(row["supervisor_id"])
            if record:
                records.append(record)
        return records
