"""Speculative reasoning engine for Brain 0.13."""

from __future__ import annotations

from typing import Any

from .claim_types import (
    ActionPermission,
    ClaimType,
    EvidenceLevel,
    GROUNDED_EVIDENCE_LEVELS,
)
from .discipline import run_full_discipline_check
from .hypothesis import HypothesisRecord
from .hypothesis_store import (
    count_by_status,
    get_hypothesis,
    init_speculation_schema,
    list_by_status,
    list_open_hypotheses,
    persist_hypothesis,
    record_review,
    update_hypothesis_status,
)

_CLASSIFIER_PATTERNS = [
    (ClaimType.COUNTERFACTUAL.value, ["if it had", "if it hadn't", "would have", "if instead", "counterfactual"]),
    (ClaimType.PREDICTION.value, ["will likely", "will probably", "expected to", "going forward", "prediction"]),
    (ClaimType.SPECULATION.value, ["might be", "could be", "possibly", "perhaps", "may indicate", "one theory"]),
    (ClaimType.HYPOTHESIS.value, ["hypothesis", "working theory", "tentatively"]),
    (ClaimType.INFERENCE.value, ["this suggests", "this implies", "based on", "therefore"]),
    (ClaimType.MEMORY.value, ["previously recorded", "event log shows", "memory says"]),
    (ClaimType.OBSERVATION.value, ["sensor reads", "measured", "directly observed", "logged value"]),
]


class SpeculativeEngine:
    def __init__(self, conn=None):
        if conn is None:
            from ..memory.store import get_store
            conn = get_store()._conn()
        self.conn = conn
        init_speculation_schema(self.conn)

    def classify_claim(self, text: str, context: dict | None = None) -> dict[str, Any]:
        lowered = (text or "").lower()
        for claim_type, patterns in _CLASSIFIER_PATTERNS:
            hits = [pattern for pattern in patterns if pattern in lowered]
            if hits:
                return {
                    "claim_type": claim_type,
                    "confidence": min(0.4 + 0.15 * len(hits), 0.85),
                    "matched_patterns": hits,
                }
        return {"claim_type": ClaimType.UNKNOWN.value, "confidence": 0.2, "matched_patterns": []}

    def create_hypothesis(
        self,
        session_uuid: str,
        claim_text: str,
        claim_type: str | None = None,
        evidence_level: str = EvidenceLevel.UNKNOWN.value,
        confidence: float = 0.3,
        supporting_evidence: list[dict] | None = None,
        contradicting_evidence: list[dict] | None = None,
        falsification_path: str = "",
        resolution_path: str = "",
        source: str = "unknown",
        action_permission: str | None = None,
    ) -> dict[str, Any]:
        if claim_type is None:
            classified = self.classify_claim(claim_text)
            claim_type = classified["claim_type"]
            if confidence == 0.3:
                confidence = classified["confidence"]
        record = HypothesisRecord(
            claim_text=claim_text,
            claim_type=claim_type,
            session_uuid=session_uuid,
            evidence_level=evidence_level,
            confidence=confidence,
            supporting_evidence=supporting_evidence or [],
            contradicting_evidence=contradicting_evidence or [],
            falsification_path=falsification_path,
            resolution_path=resolution_path,
            source=source,
            action_permission=action_permission,
        )
        report = run_full_discipline_check(record.claim_text, record.claim_type, record.evidence_level, record.action_permission)
        if not report["valid"]:
            raise ValueError(f"Discipline check failed: {report['failures']}")
        hypothesis_id = persist_hypothesis(self.conn, record)
        return {"ok": True, "hypothesis_id": hypothesis_id, "record": record.to_dict()}

    def review_hypothesis(self, hypothesis_id: str, reviewer: str = "system", review_type: str = "automated", notes: str = "") -> dict[str, Any]:
        existing = get_hypothesis(self.conn, hypothesis_id)
        if existing is None:
            return {"ok": False, "error": f"Hypothesis not found: {hypothesis_id}"}
        support_n = len(existing["supporting_evidence"])
        contra_n = len(existing["contradicting_evidence"])
        new_status = existing["status"]
        new_evidence = existing["evidence_level"]
        if contra_n > support_n and contra_n > 0:
            new_status = "contradicted" if contra_n >= 2 else "weakened"
            new_evidence = "contradicted" if contra_n >= 2 else "weakly_supported"
        elif support_n > contra_n and support_n > 0:
            new_status = "strengthened"
            new_evidence = "supported" if support_n >= 2 else "weakly_supported"
        review_id = record_review(
            self.conn,
            hypothesis_id,
            reviewer=reviewer,
            review_type=review_type,
            new_status=new_status,
            new_evidence_level=new_evidence,
            notes=notes or f"support={support_n} contradict={contra_n}",
        )
        return {"ok": True, "review_id": review_id, "new_status": new_status, "new_evidence_level": new_evidence}

    def compare_hypotheses(self, hypothesis_ids: list[str]) -> dict[str, Any]:
        records = []
        missing = []
        for hypothesis_id in hypothesis_ids:
            row = get_hypothesis(self.conn, hypothesis_id)
            if row:
                records.append(row)
            else:
                missing.append(hypothesis_id)
        ranked = sorted(
            records,
            key=lambda row: (
                row["evidence_level"] in GROUNDED_EVIDENCE_LEVELS,
                len(row["supporting_evidence"]) - len(row["contradicting_evidence"]),
                row["confidence"],
            ),
            reverse=True,
        )
        return {"ok": True, "missing": missing, "ranked_hypothesis_ids": [row["hypothesis_id"] for row in ranked], "records": ranked}

    def promote_or_demote_hypothesis(self, hypothesis_id: str, supervisor_approved: bool = False) -> dict[str, Any]:
        existing = get_hypothesis(self.conn, hypothesis_id)
        if existing is None:
            return {"ok": False, "error": f"Hypothesis not found: {hypothesis_id}"}
        grounded = existing["evidence_level"] in GROUNDED_EVIDENCE_LEVELS
        if existing["evidence_level"] == EvidenceLevel.CONTRADICTED.value:
            new_permission = ActionPermission.FORBIDDEN_FOR_ACTION.value
            action = "demoted"
        elif grounded and supervisor_approved:
            new_permission = ActionPermission.MAY_RECOMMEND.value
            action = "promoted"
        else:
            new_permission = ActionPermission.REQUIRES_SUPERVISOR_REVIEW.value
            action = "held"
        report = run_full_discipline_check(existing["claim_text"], existing["claim_type"], existing["evidence_level"], new_permission)
        if not report["valid"]:
            return {"ok": False, "error": report["failures"]}
        self.conn.execute(
            "UPDATE speculative_hypotheses SET action_permission=?, updated_at=datetime('now') WHERE hypothesis_id=?",
            (new_permission, hypothesis_id),
        )
        self.conn.commit()
        record_review(self.conn, hypothesis_id, reviewer="system", review_type="promotion_check", notes=f"{action}: {new_permission}")
        return {"ok": True, "action": action, "new_action_permission": new_permission}

    def build_speculative_summary(self, session_uuid: str) -> dict[str, Any]:
        open_rows = list_open_hypotheses(self.conn, session_uuid=session_uuid, limit=10)
        contradicted = list_by_status(self.conn, "contradicted", limit=5)
        strengthened = list_by_status(self.conn, "strengthened", limit=5)
        counts = count_by_status(self.conn)
        return {
            "open_hypotheses": open_rows,
            "unresolved_speculative_claims": [row for row in open_rows if row["claim_type"] in {"hypothesis", "speculation", "prediction", "counterfactual", "unknown"}],
            "contradicted_hypotheses": contradicted,
            "recently_strengthened_hypotheses": strengthened,
            "counts_by_status": counts,
            "unresolved_count": int(counts.get("open", 0)) + int(counts.get("weakened", 0)),
        }
