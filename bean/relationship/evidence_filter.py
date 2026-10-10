"""BEAN Lab 010: experimental evidence-based, domain-specific trust filter.

This is a reliability estimator, NOT a measure of a person's worth,
affection, obedience, subjective state, or permission to operate BEAN.
The host must authenticate verifier references and provenance independently.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from ..memory.store import get_store

MODEL_VERSION = "evidence-trust-0.8-lab010"
HALF_LIFE_DAYS = 90.0
SCHEMA = """
CREATE TABLE IF NOT EXISTS trust_v08_observations (
 evidence_id TEXT PRIMARY KEY,
 subject_id TEXT NOT NULL,
 domain TEXT NOT NULL,
 origin_id TEXT NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('success','failure')),
 verified INTEGER NOT NULL,
 verifier_ref TEXT,
 observed_at TEXT NOT NULL,
 recorded_at TEXT NOT NULL,
 detail TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_v08_subject_domain
ON trust_v08_observations(subject_id,domain,observed_at);
"""

def _date(value=None):
    if value is None:
        return datetime.now(timezone.utc)
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamps require timezone offsets")
    return dt.astimezone(timezone.utc)

def _id(value, field):
    value = str(value or "").strip()
    if not value or len(value) > 256:
        raise ValueError(f"{field} must be nonempty, at most 256 characters")
    return value

class TrustEvidenceFilter:
    """Stores raw observations immutably; calculates trust only from verified outcomes."""
    def __init__(self):
        self.store = get_store()
        self.store._conn().executescript(SCHEMA)
        self.store.commit()

    def record(self, *, evidence_id, subject_id, domain, origin_id, outcome,
               verified=False, verifier_ref=None, observed_at=None, detail=""):
        fields = {
            "evidence_id": _id(evidence_id, "evidence_id"),
            "subject_id": _id(subject_id, "subject_id"),
            "domain": _id(domain, "domain"),
            "origin_id": _id(origin_id, "origin_id"),
        }
        if outcome not in ("success", "failure"):
            raise ValueError("outcome must be success or failure")
        if verified and not verifier_ref:
            raise ValueError("verified evidence requires an independent verifier reference")
        t = _date(observed_at).isoformat()
        payload = (*fields.values(), outcome, int(bool(verified)),
                   str(verifier_ref or ""), t, str(detail or "")[:1000])
        existing = self.store.fetchone(
            "SELECT subject_id,domain,origin_id,outcome,verified,verifier_ref,observed_at,detail "
            "FROM trust_v08_observations WHERE evidence_id=?",
            (fields["evidence_id"],))
        if existing is not None:
            if tuple(existing) != payload[1:]:
                raise ValueError("immutable evidence_id collision")
            return False
        self.store.execute(
            "INSERT INTO trust_v08_observations "
            "(evidence_id,subject_id,domain,origin_id,outcome,verified,verifier_ref,"
            "observed_at,detail,recorded_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (*payload, _date().isoformat()))
        self.store.commit()
        return True

    def evaluate(self, subject_id, domain, *, as_of=None):
        subject_id, domain = _id(subject_id, "subject_id"), _id(domain, "domain")
        now = _date(as_of)
        rows = self.store.fetchall(
            "SELECT * FROM trust_v08_observations WHERE subject_id=? AND domain=? "
            "AND observed_at<=? ORDER BY observed_at DESC, evidence_id DESC",
            (subject_id, domain, now.isoformat()))
        # Correlated repeats from one origin cannot become independent votes.
        latest = {}
        excluded = []
        for raw in rows:
            r = dict(raw)
            if not r["verified"] or not r["verifier_ref"]:
                excluded.append(r["evidence_id"])
                continue
            latest.setdefault(r["origin_id"], r)
        alpha = beta = 1.0  # deliberately weak, symmetric prior
        receipts = []
        for r in latest.values():
            days = max(0.0, (now - _date(r["observed_at"])).total_seconds() / 86400)
            weight = 0.5 ** (days / HALF_LIFE_DAYS)
            alpha += weight if r["outcome"] == "success" else 0.0
            beta += weight if r["outcome"] == "failure" else 0.0
            receipts.append({
                "evidence_id": r["evidence_id"], "origin_id": r["origin_id"],
                "outcome": r["outcome"], "verifier_ref": r["verifier_ref"],
                "weight": round(weight, 5)})
        mean = alpha / (alpha + beta)
        sd = math.sqrt(alpha * beta / ((alpha + beta) ** 2 * (alpha + beta + 1)))
        # Approximate descriptive interval, not a validated statistical calibration.
        lower = max(0.0, mean - 1.645 * sd)
        upper = min(1.0, mean + 1.645 * sd)
        effective = alpha + beta - 2
        if len(receipts) < 3 or effective < 2:
            verdict = "insufficient_evidence"
        elif upper < 0.5:
            verdict = "caution"
        elif lower > 0.6:
            verdict = "supported"
        else:
            verdict = "provisional"
        return {
            "model": MODEL_VERSION, "subject_id": subject_id, "domain": domain,
            "as_of": now.isoformat(), "estimate": round(mean, 5),
            "interval_approx_90": [round(lower, 5), round(upper, 5)],
            "effective_evidence": round(effective, 4),
            "independent_origins": len(receipts), "verdict": verdict,
            "receipts": receipts, "excluded_unverified": excluded,
            "note": "Research heuristic only. No operational permissions granted."}

    def bean_review(self, subject_id, domain, *, as_of=None):
        """Pass a bounded descriptive conclusion through BEAN's actual EpistemicGuard."""
        from ..cognition.epistemic_guard import CandidateClaim, EpistemicGuard
        result = self.evaluate(subject_id, domain, as_of=as_of)
        claim = CandidateClaim(
            key=f"trust.reliability.{domain}",
            content=(
                f"Verified {domain} evidence for {subject_id}: {result['verdict']}; "
                f"descriptive estimate {result['estimate']:.3f}; "
                f"{result['independent_origins']} distinct reported origins."
            ),
            source_type="verified_outcome_ledger",
            source_ref=f"trust-ledger:{MODEL_VERSION}",
            confidence=result["estimate"],
            evidence=[r["evidence_id"] for r in result["receipts"]],
            falsification_path="New independently checked outcome may change this domain-specific estimate.",
        )
        audited = EpistemicGuard().audit(claim, persist=True)
        result["bean_audit"] = audited.to_dict()
        return result
