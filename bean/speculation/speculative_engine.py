"""Brain 0.13 speculative engine."""

from .discipline import run_full_discipline_check
from .hypothesis import HypothesisRecord
from .hypothesis_store import count_by_status, init_speculation_schema, list_open_hypotheses, persist_hypothesis, record_review, update_hypothesis_status


class SpeculativeEngine:
    def __init__(self, conn=None):
        self.conn = init_speculation_schema(conn)

    def classify_claim(self, text: str) -> dict:
        low = (text or "").lower()
        if "if " in low or "would have" in low: ct = "counterfactual"
        elif "will likely" in low or "probably" in low: ct = "prediction"
        elif "might" in low or "could" in low or "possibly" in low: ct = "speculation"
        elif "suggests" in low or "implies" in low: ct = "inference"
        else: ct = "unknown"
        return {"claim_type": ct, "confidence": 0.35}

    def create_hypothesis(self, session_uuid: str, claim_text: str, claim_type=None, evidence_level="unknown", confidence=0.3, source="unknown", action_permission=None, **kwargs) -> dict:
        if claim_type is None:
            found = self.classify_claim(claim_text)
            claim_type = found["claim_type"]
            confidence = found["confidence"]
        rec = HypothesisRecord(claim_text=claim_text, claim_type=claim_type, session_uuid=session_uuid, evidence_level=evidence_level, confidence=confidence, source=source, action_permission=action_permission)
        report = run_full_discipline_check(claim_text, rec.claim_type, rec.evidence_level, rec.action_permission)
        if not report["valid"]:
            raise ValueError(str(report["failures"]))
        hid = persist_hypothesis(self.conn, rec)
        return {"ok": True, "hypothesis_id": hid, "record": rec.to_dict()}

    def review_hypothesis(self, hypothesis_id: str, reviewer="system", review_type="automated", notes="") -> dict:
        rid = record_review(self.conn, hypothesis_id, reviewer, review_type, None, notes)
        return {"ok": True, "review_id": rid, "hypothesis_id": hypothesis_id}

    def compare_hypotheses(self, hypothesis_ids: list[str]) -> dict:
        return {"ok": True, "ranked_hypothesis_ids": hypothesis_ids, "compared": len(hypothesis_ids)}

    def build_speculative_summary(self, session_uuid: str) -> dict:
        return {"open_hypotheses": list_open_hypotheses(self.conn, session_uuid=session_uuid, limit=10), "counts_by_status": count_by_status(self.conn), "unresolved_count": count_by_status(self.conn).get("open", 0)}

    def promote_or_demote_hypothesis(self, hypothesis_id: str, supervisor_approved: bool = False) -> dict:
        return {"ok": True, "hypothesis_id": hypothesis_id, "new_action_permission": "requires_supervisor_review" if not supervisor_approved else "may_recommend"}
