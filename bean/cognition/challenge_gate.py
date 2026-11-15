"""Evidence-linked, owner-overridable challenge preflight in BEAN's existing SQLite Core.

This gate enforces decisions only for callers that invoke it. It does not claim
source authentication, independent reasoning, or GitHub branch protection.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from bean.memory.store import get_store


SCHEMA = """
CREATE TABLE IF NOT EXISTS challenge_reviews (
    challenge_id TEXT PRIMARY KEY,
    proposal_hash TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    revision TEXT NOT NULL,
    summary TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN ('allow','block')),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_challenge_proposal
    ON challenge_reviews(proposal_hash, created_at);
CREATE TABLE IF NOT EXISTS challenge_objections (
    objection_id TEXT PRIMARY KEY,
    challenge_id TEXT NOT NULL REFERENCES challenge_reviews(challenge_id),
    kind TEXT NOT NULL CHECK(kind IN ('conflict','reckless')),
    reason TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS challenge_overrides (
    override_id TEXT PRIMARY KEY,
    challenge_id TEXT NOT NULL UNIQUE REFERENCES challenge_reviews(challenge_id),
    actor TEXT NOT NULL,
    justification TEXT NOT NULL,
    actor_authentication TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

# The source ID has to exist in an already-established BEAN evidence table.
# Existence establishes a receipt, not the truth or relevance of its contents.
EVIDENCE_TYPES = {
    "epistemic_audit": ("epistemic_audits", "audit_id"),
    "claim_conflict": ("claim_conflicts", "conflict_id"),
    "claim_verdict": ("claim_verdicts", "verdict_id"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(value: object, label: str, limit: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label} must be nonempty text of at most {limit} characters")
    return value.strip()


@dataclass(frozen=True)
class Proposal:
    action: str
    target: str
    revision: str
    summary: str

    def normalized(self) -> dict[str, str]:
        return {
            "action": _string(self.action, "action", 100),
            "target": _string(self.target, "target", 400),
            "revision": _string(self.revision, "revision", 200),
            "summary": _string(self.summary, "summary", 2000),
        }

    def fingerprint(self) -> str:
        payload = json.dumps(self.normalized(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ChallengeGate:
    """Append-only objections and overrides, bound to one exact proposal digest."""

    def __init__(self):
        self.store = get_store()
        self.store._conn().executescript(SCHEMA)
        self.store.commit()

    def _verify_refs(self, refs: object) -> list[str]:
        if not isinstance(refs, list) or not 1 <= len(refs) <= 12:
            raise ValueError("Each objection needs 1..12 actual BEAN evidence references")
        checked = []
        for raw in refs:
            ref = _string(raw, "evidence reference", 240)
            kind, separator, source_id = ref.partition(":")
            if not separator or kind not in EVIDENCE_TYPES or not source_id:
                raise ValueError(f"Unsupported evidence reference: {ref}")
            table, key = EVIDENCE_TYPES[kind]
            if not self.store.fetchone(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ):
                raise ValueError(f"Evidence table unavailable for {kind}")
            if not self.store.fetchone(f"SELECT 1 FROM {table} WHERE {key}=?", (source_id,)):
                raise ValueError(f"Evidence receipt not found: {ref}")
            if ref not in checked:
                checked.append(ref)
        return checked

    def _objections(self, objections: object) -> list[dict]:
        if not isinstance(objections, list) or len(objections) > 12:
            raise ValueError("objections must be a list of at most 12 entries")
        reviewed = []
        for entry in objections:
            if not isinstance(entry, dict) or set(entry) != {"kind", "reason", "evidence_refs"}:
                raise ValueError("Objection needs kind, reason and evidence_refs only")
            if entry["kind"] not in ("conflict", "reckless"):
                raise ValueError("Objection kind must be conflict or reckless")
            reviewed.append({
                "kind": entry["kind"],
                "reason": _string(entry["reason"], "objection reason", 1500),
                "evidence_refs": self._verify_refs(entry["evidence_refs"]),
            })
        return reviewed

    def review(self, proposal: Proposal, objections: list[dict]) -> dict:
        data = proposal.normalized()
        fingerprint = proposal.fingerprint()
        # Never let omitting objections on a subsequent call erase an open block.
        pending = self.store.fetchone(
            "SELECT r.challenge_id FROM challenge_reviews r "
            "LEFT JOIN challenge_overrides o ON o.challenge_id=r.challenge_id "
            "WHERE r.proposal_hash=? AND r.decision='block' AND o.override_id IS NULL "
            "ORDER BY r.rowid DESC LIMIT 1", (fingerprint,)
        )
        if pending:
            return self.status(pending["challenge_id"])
        evaluated = self._objections(objections)
        if not evaluated:
            last = self.store.fetchone(
                "SELECT challenge_id FROM challenge_reviews WHERE proposal_hash=? "
                "ORDER BY rowid DESC LIMIT 1", (fingerprint,)
            )
            if last:
                return self.status(last["challenge_id"])
        challenge_id = str(uuid.uuid4())
        decision = "block" if evaluated else "allow"
        created = _now()
        self.store.execute(
            "INSERT INTO challenge_reviews "
            "(challenge_id,proposal_hash,action,target,revision,summary,decision,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (challenge_id, fingerprint, data["action"], data["target"],
             data["revision"], data["summary"], decision, created),
        )
        for entry in evaluated:
            self.store.execute(
                "INSERT INTO challenge_objections "
                "(objection_id,challenge_id,kind,reason,evidence_refs_json,created_at) "
                "VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4()), challenge_id, entry["kind"], entry["reason"],
                 json.dumps(entry["evidence_refs"]), created),
            )
        self.store.commit()
        return self.status(challenge_id)

    def override(self, challenge_id: str, *, actor: str, justification: str) -> dict:
        challenge_id = _string(challenge_id, "challenge_id", 60)
        actor = _string(actor, "override actor", 200)
        justification = _string(justification, "override justification", 2000)
        if self.store.fetchone(
            "SELECT 1 FROM challenge_overrides WHERE challenge_id=?", (challenge_id,)
        ):
            raise ValueError("Already overridden; the original record cannot be edited")
        decision = self.store.fetchone(
            "SELECT decision FROM challenge_reviews WHERE challenge_id=?", (challenge_id,)
        )
        if decision is None or decision["decision"] != "block":
            raise ValueError("Override requires an existing blocked challenge")
        self.store.execute(
            "INSERT INTO challenge_overrides "
            "(override_id,challenge_id,actor,justification,actor_authentication,created_at) "
            "VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), challenge_id, actor, justification,
             "caller_supplied_not_authenticated_by_core", _now()),
        )
        self.store.commit()
        return self.status(challenge_id)

    def status(self, challenge_id: str) -> dict:
        review = self.store.fetchone(
            "SELECT * FROM challenge_reviews WHERE challenge_id=?", (challenge_id,)
        )
        if review is None:
            raise ValueError("Challenge ID not found")
        objections = self.store.fetchall(
            "SELECT kind,reason,evidence_refs_json FROM challenge_objections "
            "WHERE challenge_id=? ORDER BY rowid", (challenge_id,)
        )
        override = self.store.fetchone(
            "SELECT override_id,actor,justification,actor_authentication,created_at "
            "FROM challenge_overrides WHERE challenge_id=?", (challenge_id,)
        )
        state = "OVERRIDDEN" if override else ("BLOCK" if review["decision"] == "block" else "ALLOW")
        return {
            "challenge_id": review["challenge_id"],
            "proposal_sha256": review["proposal_hash"],
            "proposal": {key: review[key] for key in ("action", "target", "revision", "summary")},
            "decision": state,
            "may_proceed": state != "BLOCK",
            "objections": [{
                "kind": row["kind"], "reason": row["reason"],
                "evidence_refs": json.loads(row["evidence_refs_json"]),
                "evidence_provenance": "receipt_exists; truth_and_relevance_not_independently_verified",
            } for row in objections],
            "override": dict(override) if override else None,
            "created_at": review["created_at"],
        }
