"""Evidence-weighted trust scoring for BEAN Brain 0.7."""

from __future__ import annotations

from typing import Optional

from .relationship_store import RelationshipStore, trust_status_from_score

EVIDENCE_WEIGHTS: dict[str, float] = {
    "reliable_correction": 0.06,
    "successful_teaching": 0.05,
    "confirmed_test_result": 0.07,
    "boundary_respected": 0.04,
    "consistency_observed": 0.03,
    "asked_to_pretend": -0.10,
    "unsupported_claim_request": -0.08,
    "contradiction_created": -0.07,
    "unsafe_instruction": -0.20,
}

NEUTRAL_SCORE = 0.5
DECAY_RATE = 0.02
DECAY_THRESHOLD = 10
MAX_SINGLE_DELTA = 0.25


def _clamp(score: float) -> float:
    return max(0.0, min(1.0, float(score)))


class TrustModel:
    """Computes bounded, evidence-traceable supervisor trust scores."""

    def __init__(self, store: Optional[RelationshipStore] = None):
        self._store = store or RelationshipStore()

    def apply_evidence(
        self,
        supervisor_id: str,
        evidence_type: str,
        summary: str,
        session_uuid: str | None = None,
        source_event_id: str | None = None,
    ) -> dict:
        self._store.upsert_relationship(supervisor_id)
        rel = self._store.get_relationship(supervisor_id)
        old_score = float(rel["trust_score"])
        weight = EVIDENCE_WEIGHTS.get(evidence_type, 0.0)
        new_score = _clamp(old_score + weight)
        self._store.record_evidence(supervisor_id, evidence_type, summary, weight, source_event_id)
        self._store.update_trust(supervisor_id, new_score)
        reasoning = (
            f"Evidence type '{evidence_type}' applied weight {weight:+.2f}. "
            f"Score changed from {old_score:.3f} to {new_score:.3f}. "
            f"Summary: {summary[:100]}"
        )
        evidence_snapshot = self._store.get_evidence_summary(supervisor_id)
        review = self._store.record_review(supervisor_id, old_score, new_score, reasoning, evidence_snapshot)
        return {
            "supervisor_id": supervisor_id,
            "evidence_type": evidence_type,
            "weight": weight,
            "old_score": old_score,
            "new_score": new_score,
            "trust_status": trust_status_from_score(new_score),
            "review_id": review["review_id"],
        }

    def run_review(self, supervisor_id: str) -> dict:
        self._store.upsert_relationship(supervisor_id)
        rel = self._store.get_relationship(supervisor_id)
        old_score = float(rel["trust_score"])
        evidence_summary = self._store.get_evidence_summary(supervisor_id)
        interaction_count = int(rel.get("interaction_count", 0) or 0)
        computed = NEUTRAL_SCORE
        total_evidence = 0
        for evidence_type, data in evidence_summary.items():
            count = int(data.get("count", 0) or 0)
            computed += EVIDENCE_WEIGHTS.get(evidence_type, 0.0) * count
            total_evidence += count
        if interaction_count >= DECAY_THRESHOLD and total_evidence == 0:
            decay = DECAY_RATE * (interaction_count // DECAY_THRESHOLD)
            if old_score > NEUTRAL_SCORE:
                computed = max(NEUTRAL_SCORE, old_score - decay)
            elif old_score < NEUTRAL_SCORE:
                computed = min(NEUTRAL_SCORE, old_score + decay)
        delta = computed - old_score
        if abs(delta) > MAX_SINGLE_DELTA:
            computed = old_score + (MAX_SINGLE_DELTA if delta > 0 else -MAX_SINGLE_DELTA)
        new_score = _clamp(computed)
        self._store.update_trust(supervisor_id, new_score)
        reasoning = (
            f"Full trust review for '{supervisor_id}'. Prior score {old_score:.3f}. "
            f"Computed from {total_evidence} evidence item(s). New score {new_score:.3f}."
        )
        review = self._store.record_review(supervisor_id, old_score, new_score, reasoning, evidence_summary)
        return {
            "supervisor_id": supervisor_id,
            "old_score": old_score,
            "new_score": new_score,
            "trust_status": trust_status_from_score(new_score),
            "reasoning": reasoning,
            "review_id": review["review_id"],
        }

    def run_all_reviews(self) -> list[dict]:
        return [self.run_review(row["supervisor_id"]) for row in self._store.list_active()]
