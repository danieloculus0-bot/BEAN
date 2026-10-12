"""BEAN Core: domain-neutral, evidence-first ranking and scored memory receipts.

Scores describe evidence strength, not the probability a statement is true.
Host attestations do not independently establish real-world truth. This module
neither trades, executes code, nor authorizes physical or external actions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3

VERSION = "bean.evidence.rank.v1"
_SCHEMA = """
CREATE TABLE IF NOT EXISTS bean_ranked_evidence (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  evidence_id TEXT NOT NULL UNIQUE,
  domain TEXT NOT NULL,
  topic TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  intake_score INTEGER NOT NULL CHECK(intake_score BETWEEN 0 AND 99),
  payload_sha256 TEXT NOT NULL,
  previous_hash TEXT NOT NULL,
  entry_hash TEXT NOT NULL,
  recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS bean_ranked_evidence_subject
  ON bean_ranked_evidence(domain,topic,seq);
"""


def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _date(raw: str) -> datetime:
    try:
        date = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError("observed_at must be an ISO 8601 timestamp") from exc
    if date.utcoffset() is None:
        raise ValueError("observed_at must include a timezone")
    return date.astimezone(timezone.utc)


@dataclass(frozen=True)
class Evidence:
    """Host-supplied observation: provenance and verification are assertions."""
    evidence_id: str
    domain: str
    topic: str
    value: str
    origin: str
    source_ref: str
    observed_at: str
    verified: bool = False
    verification_ref: str | None = None
    outcome: str = "unmeasured"
    outcome_ref: str | None = None

    def __post_init__(self):
        for field in ("evidence_id", "domain", "topic", "value", "origin", "source_ref"):
            v = getattr(self, field)
            if not isinstance(v, str) or not v.strip() or len(v) > (2000 if field == "value" else 500):
                raise ValueError(f"invalid {field}")
        if type(self.verified) is not bool:
            raise ValueError("verified must be an explicit boolean")
        if self.verified:
            if not isinstance(self.verification_ref, str) or not self.verification_ref.strip():
                raise ValueError("host-attested evidence requires a verification_ref")
            if self.verification_ref == self.source_ref:
                raise ValueError("verification_ref cannot equal source_ref")
        elif self.verification_ref is not None:
            raise ValueError("unverified evidence cannot claim a verification_ref")
        if self.outcome not in {"pass", "fail", "unmeasured"}:
            raise ValueError("outcome must be pass, fail, or unmeasured")
        if self.outcome == "unmeasured" and self.outcome_ref is not None:
            raise ValueError("unmeasured evidence cannot carry an outcome_ref")
        if self.outcome != "unmeasured":
            if not self.verified or not isinstance(self.outcome_ref, str) or not self.outcome_ref.strip():
                raise ValueError("measured outcomes require host attestation and an outcome_ref")
            if self.outcome_ref in {self.source_ref, self.verification_ref}:
                raise ValueError("outcome_ref must be separate from source and verification")
        _date(self.observed_at)


class EvidenceRankLedger:
    """Score BEFORE hash/persistence; retain original scores and recompute rankings.

    The current rank is revisable on new evidence. The append-only intake
    receipt is immutable and hash-chained; it does not authenticate origins.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.executescript(_SCHEMA)
        self.conn.commit()
        self.verify_chain()

    @staticmethod
    def _rank(rows: list[dict], now: datetime) -> list[dict]:
        values = sorted({r["value"] for r in rows})
        attested_values = {r["value"] for r in rows if r["verified"]}
        contested = len(attested_values) > 1
        result = []
        for value in values:
            group = [r for r in rows if r["value"] == value]
            verified = [r for r in group if r["verified"]]
            # Repeated copies from one named origin count as one origin.
            supporting_origins = {r["origin"].casefold().strip() for r in verified}
            opposing_origins = {r["origin"].casefold().strip() for r in rows
                                if r["verified"] and r["value"] != value}
            passing = {r["origin"].casefold().strip() for r in verified if r["outcome"] == "pass"}
            failing = {r["origin"].casefold().strip() for r in verified if r["outcome"] == "fail"}
            latest = max(_date(r["observed_at"]) for r in (verified or group))
            days = max(0, int((now - latest).total_seconds() // 86400))
            age_penalty = min(24, (days // 30) * 4)
            # Tunable ranking heuristic, never a calibrated probability.
            score = 12 + (28 if supporting_origins else 0)
            score += min(3, max(0, len(supporting_origins) - 1)) * 14
            score += min(2, len(passing)) * 8
            score -= min(2, len(failing)) * 14
            score -= min(3, len(opposing_origins)) * 15
            score -= age_penalty
            score = max(0, min(99, score))
            status = ("contested" if contested else
                      "attested" if len(supporting_origins) >= 2 else
                      "insufficient")
            result.append({"value": value, "score": score, "status": status,
                           "distinct_verified_origins": len(supporting_origins),
                           "opposing_verified_origins": len(opposing_origins),
                           "observations": len(group), "pass_origins": len(passing),
                           "fail_origins": len(failing), "age_days": days,
                           "score_is_truth_probability": False})
        return sorted(result, key=lambda x: (-x["score"], x["value"]))

    @staticmethod
    def _now(as_of: datetime | None) -> datetime:
        now = as_of or datetime.now(timezone.utc)
        if not isinstance(now, datetime) or now.utcoffset() is None:
            raise ValueError("as_of must have a timezone")
        return now.astimezone(timezone.utc)

    def rank(self, domain: str, topic: str, *, as_of: datetime | None = None) -> list[dict]:
        self.verify_chain()
        now = self._now(as_of)
        rows = self.conn.execute(
            "SELECT payload_json FROM bean_ranked_evidence WHERE domain=? AND topic=? "
            "AND recorded_at<=? ORDER BY seq",
            (domain, topic, now.isoformat()),
        ).fetchall()
        return self._rank([r for r in (json.loads(row[0]) for row in rows)
                           if _date(r["observed_at"]) <= now], now)

    def observe(self, evidence: Evidence, *, as_of: datetime | None = None, commit: bool = True) -> dict:
        if not isinstance(evidence, Evidence):
            raise TypeError("provide a validated Evidence record")
        self.verify_chain()
        now = self._now(as_of)
        observed = _date(evidence.observed_at)
        if observed > now:
            raise ValueError("future observations cannot be scored as evidence")
        payload = asdict(evidence)
        payload["observed_at"] = observed.isoformat()
        payload_json = _canonical(payload)
        existing = self.conn.execute(
            "SELECT payload_json,intake_score,entry_hash FROM bean_ranked_evidence WHERE evidence_id=?",
            (evidence.evidence_id,),
        ).fetchone()
        if existing:
            if existing[0] != payload_json:
                raise ValueError("evidence_id collision with changed content")
            return {"new": False, "intake_score": existing[1], "hash": existing[2], "schema": VERSION}
        prior = [json.loads(r[0]) for r in self.conn.execute(
            "SELECT payload_json FROM bean_ranked_evidence WHERE domain=? AND topic=?",
            (evidence.domain, evidence.topic),
        )]
        ranking = self._rank(prior + [payload], now)
        intake_score = next(row["score"] for row in ranking if row["value"] == evidence.value)
        previous = self.conn.execute(
            "SELECT entry_hash FROM bean_ranked_evidence ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous[0] if previous else "GENESIS"
        payload_hash = _hash(payload_json)
        envelope = _canonical({"payload_hash": payload_hash, "intake_score": intake_score,
                               "previous_hash": previous_hash, "schema": VERSION})
        entry_hash = _hash(envelope)
        self.conn.execute(
            "INSERT INTO bean_ranked_evidence(evidence_id,domain,topic,payload_json,"
            "intake_score,payload_sha256,previous_hash,entry_hash,recorded_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (evidence.evidence_id, evidence.domain, evidence.topic, payload_json,
             intake_score, payload_hash, previous_hash, entry_hash, now.isoformat()),
        )
        if commit:
            self.conn.commit()
        return {"new": True, "intake_score": intake_score, "hash": entry_hash, "schema": VERSION}

    def verify_chain(self) -> bool:
        previous = "GENESIS"
        for row in self.conn.execute(
            "SELECT payload_json,intake_score,payload_sha256,previous_hash,entry_hash "
            "FROM bean_ranked_evidence ORDER BY seq"
        ):
            payload_json, score, digest, old, entry = row
            if not isinstance(score, int) or not 0 <= score <= 99:
                raise ValueError("BEAN evidence ranking score tampered")
            if (digest != _hash(payload_json) or old != previous or
                entry != _hash(_canonical({"payload_hash": digest, "intake_score": score,
                                          "previous_hash": previous, "schema": VERSION}))):
                raise ValueError("BEAN evidence rank chain failed verification")
            previous = entry
        return True
