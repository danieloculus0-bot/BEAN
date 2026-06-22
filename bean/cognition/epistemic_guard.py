"""Epistemic guard for BEAN Brain 0.3.

The guard screens candidate claims before they become active identity/world
memory. It rejects or downgrades unsupported self-claims, capability inflation,
fake emotion/sentience language, and claims with no evidence or falsification
path.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

EPISTEMIC_SCHEMA = """
CREATE TABLE IF NOT EXISTS epistemic_audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT NOT NULL UNIQUE,
    candidate_key TEXT NOT NULL,
    candidate_content TEXT NOT NULL,
    verdict TEXT NOT NULL,
    reasons TEXT NOT NULL,
    repaired_content TEXT,
    source_ref TEXT,
    confidence REAL,
    falsification_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_epistemic_verdict ON epistemic_audits(verdict);
CREATE INDEX IF NOT EXISTS idx_epistemic_key ON epistemic_audits(candidate_key);
"""


class EpistemicVerdict(str, Enum):
    APPROVED = "approved"
    DOWNGRADED = "downgraded"
    REJECTED = "rejected"


FAKE_EMOTION_PATTERNS = [
    r"\bi feel\b",
    r"\bi felt\b",
    r"\bi am scared\b",
    r"\bi am afraid\b",
    r"\bi am happy\b",
    r"\bi am sad\b",
    r"\bi love\b",
    r"\bi hate\b",
]

FAKE_SENTIENCE_PATTERNS = [
    r"\bi am sentient\b",
    r"\bi am conscious\b",
    r"\bi am alive\b",
    r"\bi have a soul\b",
    r"\bi understand\b",
    r"\bi chose\b",
    r"\bi decided\b",
]

CAPABILITY_INFLATION_PATTERNS = [
    r"\bi can move\b",
    r"\bi moved\b",
    r"\bi can see\b",
    r"\bi can hear\b",
    r"\bi can act autonomously\b",
    r"\bi learned\b",
]


@dataclass
class CandidateClaim:
    key: str
    content: str
    source_type: Optional[str] = None
    source_ref: Optional[str] = None
    confidence: Optional[float] = None
    evidence: list[str] = field(default_factory=list)
    falsification_path: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EpistemicAudit:
    candidate_key: str
    candidate_content: str
    verdict: EpistemicVerdict
    reasons: list[str]
    repaired_content: Optional[str] = None
    source_ref: Optional[str] = None
    confidence: Optional[float] = None
    falsification_path: Optional[str] = None
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "audit_id": self.audit_id,
            "candidate_key": self.candidate_key,
            "candidate_content": self.candidate_content,
            "verdict": self.verdict.value,
            "reasons": self.reasons,
            "repaired_content": self.repaired_content,
            "source_ref": self.source_ref,
            "confidence": self.confidence,
            "falsification_path": self.falsification_path,
            "created_at": self.created_at,
        }


def ensure_epistemic_tables():
    from ..memory.store import get_store
    store = get_store()
    store._conn().executescript(EPISTEMIC_SCHEMA)
    store.commit()


class EpistemicGuard:
    def __init__(self):
        ensure_epistemic_tables()

    def audit(self, candidate: CandidateClaim, persist: bool = True) -> EpistemicAudit:
        reasons: list[str] = []
        content = candidate.content.strip()
        lowered = content.lower()

        if not candidate.source_type and not candidate.source_ref:
            reasons.append("missing_source")
        if candidate.confidence is None:
            reasons.append("missing_confidence")
        elif not 0.0 <= float(candidate.confidence) <= 1.0:
            reasons.append("invalid_confidence")
        if not candidate.evidence and not candidate.source_ref:
            reasons.append("missing_evidence")
        if not candidate.falsification_path:
            reasons.append("missing_falsification_path")

        if self._matches(lowered, FAKE_EMOTION_PATTERNS):
            reasons.append("fake_emotion_language")
        if self._matches(lowered, FAKE_SENTIENCE_PATTERNS):
            reasons.append("fake_sentience_or_agency_language")
        if self._matches(lowered, CAPABILITY_INFLATION_PATTERNS):
            if self._capability_not_proven(candidate):
                reasons.append("capability_inflation")

        active_conflict = self._active_conflict(candidate)
        if active_conflict:
            reasons.append(f"contradicts_active_claim:{active_conflict}")

        if any(r in reasons for r in ("fake_emotion_language", "fake_sentience_or_agency_language", "capability_inflation")):
            verdict = EpistemicVerdict.REJECTED
            repaired = self._repair_content(content, reasons)
        elif reasons:
            verdict = EpistemicVerdict.DOWNGRADED
            repaired = self._repair_content(content, reasons)
        else:
            verdict = EpistemicVerdict.APPROVED
            repaired = None

        audit = EpistemicAudit(
            candidate_key=candidate.key,
            candidate_content=content,
            verdict=verdict,
            reasons=reasons or ["claim_passed_guard"],
            repaired_content=repaired,
            source_ref=candidate.source_ref,
            confidence=candidate.confidence,
            falsification_path=candidate.falsification_path,
        )
        if persist:
            self.persist(audit)
        return audit

    def persist(self, audit: EpistemicAudit):
        from ..memory.store import get_store
        get_store().execute(
            """
            INSERT OR IGNORE INTO epistemic_audits
                (audit_id, candidate_key, candidate_content, verdict, reasons,
                 repaired_content, source_ref, confidence, falsification_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit.audit_id,
                audit.candidate_key,
                audit.candidate_content,
                audit.verdict.value,
                json.dumps(audit.reasons),
                audit.repaired_content,
                audit.source_ref,
                audit.confidence,
                audit.falsification_path,
                audit.created_at,
            ),
        )
        get_store().commit()

    def audit_active_claims(self, limit: int = 200) -> list[EpistemicAudit]:
        from ..memory.store import get_store
        rows = get_store().fetchall(
            "SELECT key, content, confidence, source_ref FROM world_claims WHERE active=1 ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        audits: list[EpistemicAudit] = []
        for row in rows:
            candidate = CandidateClaim(
                key=row["key"],
                content=row["content"],
                source_ref=row["source_ref"],
                confidence=row["confidence"],
                evidence=[row["source_ref"]] if row["source_ref"] else [],
                falsification_path=None,
            )
            audits.append(self.audit(candidate))
        return audits

    def _matches(self, text: str, patterns: list[str]) -> bool:
        return any(re.search(p, text) for p in patterns)

    def _capability_not_proven(self, candidate: CandidateClaim) -> bool:
        from ..memory.store import get_store
        words = candidate.content.lower()
        risky_names = ["hardware_motion", "servo_hardware_driver", "autonomous_action", "vision", "audio"]
        for name in risky_names:
            if name.replace("_", " ") in words or name in candidate.key:
                row = get_store().fetchone("SELECT status FROM capabilities WHERE name=?", (name,))
                if not row or row["status"] != "active":
                    return True
        return any(token in words for token in ["i can move", "i moved", "act autonomously"])

    def _active_conflict(self, candidate: CandidateClaim) -> Optional[str]:
        from ..memory.store import get_store
        key = candidate.key.lower()
        text = candidate.content.lower()
        if "camera" in key or "vision" in key or "camera" in text:
            row = get_store().fetchone(
                "SELECT key FROM world_claims WHERE active=1 AND key='environment.uncertainty.no_vision' LIMIT 1"
            )
            if row and any(word in text for word in ["active", "working", "verified"]):
                return row["key"]
        if "audio" in key or "microphone" in key or "audio" in text:
            row = get_store().fetchone(
                "SELECT key FROM world_claims WHERE active=1 AND key='environment.uncertainty.no_audio' LIMIT 1"
            )
            if row and any(word in text for word in ["active", "working", "verified"]):
                return row["key"]
        return None

    def _repair_content(self, content: str, reasons: list[str]) -> str:
        if "fake_emotion_language" in reasons:
            return "Internal pressure or drive state should be reported from records instead of feeling language."
        if "fake_sentience_or_agency_language" in reasons:
            return "Claim should be reframed as an evidence-grounded record, not sentience, understanding, or agency."
        if "capability_inflation" in reasons:
            return "Capability claim should remain uncertain until supported by test or observation records."
        return f"Downgraded to uncertainty: {content}"
