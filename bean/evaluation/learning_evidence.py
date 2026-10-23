"""Auditable learning-experiment receipts for BEAN (standard library only).

Independently authored BEAN implementation of general checkpoint, trajectory,
and paired-experiment concepts. No upstream source was copied. No external
actions, model calls, or weight changes are enabled by this module.

Hashes detect altered rows within an inspected SQLite database; they do NOT
authenticate asserted origins, and an administrator can replace an entire
hash chain. Independently attest chain tips for stronger evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import sqlite3
from typing import Any, Iterable

VERSION = "bean.learning.evidence.v1"
STAGES = frozenset({"observation", "hypothesis", "experiment", "reflection", "change", "review"})
ARMS = frozenset({"control", "treatment", "placebo"})
GENESIS = "0" * 64


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, label: str, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\0" in value:
        raise ValueError(f"invalid {label}")
    return value


class LearningEvidenceLedger:
    """Append-only-by-API SQLite receipts using the caller's DB connection.

    A separate namespaced table does not replace BEAN's authoritative memory,
    its host attestations, or the canonical event logger.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bean_learning_evidence (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                claim_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                created_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS bean_learning_evidence_claim
            ON bean_learning_evidence(claim_id, seq)
        """)
        self.conn.commit()
        self.verify_chain()

    @staticmethod
    def _fields(event_id: str, claim_id: str, stage: str,
                source_ref: str, created_utc: str, payload: dict, prev_hash: str) -> dict:
        return dict(event_id=event_id, claim_id=claim_id, stage=stage,
                    source_ref=source_ref, created_utc=created_utc,
                    payload=payload, prev_hash=prev_hash)

    def verify_chain(self) -> str:
        """Return current tip, raising for a malformed or tampered receipt."""
        prev, last_seq = GENESIS, 0
        cursor = self.conn.execute("""
            SELECT seq, event_id, claim_id, stage, source_ref,
                   created_utc, payload_json, prev_hash, entry_hash
            FROM bean_learning_evidence ORDER BY seq
        """)
        for (seq, event_id, claim_id, stage, source_ref,
             created_utc, raw, prior, claimed_hash) in cursor:
            if seq <= last_seq or prior != prev:
                raise ValueError(f"learning evidence chain discontinuity at seq={seq}")
            try:
                payload = json.loads(raw)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid recorded JSON at seq={seq}") from exc
            expected = _digest(self._fields(event_id, claim_id, stage,
                                           source_ref, created_utc, payload, prior))
            if claimed_hash != expected or raw != _canonical(payload):
                raise ValueError(f"learning evidence hash mismatch at seq={seq}")
            prev, last_seq = expected, seq
        return prev

    def append(self, *, event_id: str, claim_id: str, stage: str,
               source_ref: str, payload: dict) -> dict:
        """Atomically append an observation; retry identical IDs idempotently."""
        _text(event_id, "event_id")
        _text(claim_id, "claim_id")
        _text(source_ref, "source_ref", 2000)
        if stage not in STAGES:
            raise ValueError("unrecognized learning stage")
        if not isinstance(payload, dict) or not payload:
            raise ValueError("payload must be a nonempty dictionary")
        raw = _canonical(payload)
        if len(raw.encode("utf-8")) > 65536:
            raise ValueError("payload exceeds 64 KiB")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            tip = self.verify_chain()
            existing = self.conn.execute("""
                SELECT claim_id, stage, source_ref, payload_json,
                       entry_hash, created_utc FROM bean_learning_evidence
                WHERE event_id = ?
            """, (event_id,)).fetchone()
            if existing:
                if tuple(existing[:4]) != (claim_id, stage, source_ref, raw):
                    raise ValueError("event_id collision with different content")
                self.conn.commit()
                return {"new": False, "event_id": event_id,
                        "hash": existing[4], "created_utc": existing[5]}
            timestamp = datetime.now(timezone.utc).isoformat()
            entry_hash = _digest(self._fields(event_id, claim_id, stage,
                                               source_ref, timestamp, payload, tip))
            self.conn.execute("""
                INSERT INTO bean_learning_evidence
                (event_id, claim_id, stage, source_ref, created_utc,
                 payload_json, prev_hash, entry_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (event_id, claim_id, stage, source_ref, timestamp,
                  raw, tip, entry_hash))
            self.conn.commit()
            return {"new": True, "event_id": event_id,
                    "hash": entry_hash, "created_utc": timestamp}
        except BaseException:
            self.conn.rollback()
            raise

    def history(self, claim_id: str) -> list[dict]:
        """Return verified ordered receipt history; don't claim source truth."""
        _text(claim_id, "claim_id")
        self.verify_chain()
        rows = self.conn.execute("""
            SELECT event_id, stage, source_ref, created_utc,
                   payload_json, entry_hash FROM bean_learning_evidence
            WHERE claim_id = ? ORDER BY seq
        """, (claim_id,)).fetchall()
        return [dict(event_id=event_id, stage=stage, source_ref=source_ref,
                     created_utc=timestamp, payload=json.loads(raw), hash=digest)
                for event_id, stage, source_ref, timestamp, raw, digest in rows]


@dataclass(frozen=True)
class TrialMeasurement:
    """A host-asserted outcome, not independently authenticated proof."""
    arm: str
    task_id: str
    replicate: int
    model_id: str
    model_revision: str
    document_sha256: str
    protocol_sha256: str
    budget_tokens: int
    scorer_ref: str
    run_ref: str
    score: float
    latency_ms: float

    def __post_init__(self):
        for label in ("task_id", "model_id", "model_revision",
                      "scorer_ref", "run_ref"):
            _text(getattr(self, label), label, 2000)
        if self.arm not in ARMS:
            raise ValueError("unknown arm")
        if type(self.replicate) is not int or self.replicate < 0:
            raise ValueError("invalid replicate")
        if type(self.budget_tokens) is not int or self.budget_tokens <= 0:
            raise ValueError("invalid token budget")
        for name in ("document_sha256", "protocol_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64 or any(
                c not in "0123456789abcdef" for c in value
            ):
                raise ValueError(f"invalid {name}")
        if type(self.score) not in (float, int) or not math.isfinite(self.score) or not 0 <= self.score <= 1:
            raise ValueError("score must be finite and between 0 and 1")
        if type(self.latency_ms) not in (float, int) or not math.isfinite(self.latency_ms) or self.latency_ms < 0:
            raise ValueError("latency_ms must be finite and nonnegative")


def assess_matched_trials(trials: Iterable[TrialMeasurement], min_pairs: int = 5) -> dict:
    """Validate matched triplets and report effects, never assert learning.

    Independent evaluators must still verify blinding, source cutoff, model
    identity, absence of answer leakage, and the actual changed artifact.
    """
    if type(min_pairs) is not int or min_pairs < 2:
        raise ValueError("min_pairs must be an integer >= 2")
    trials = list(trials)
    if not trials:
        raise ValueError("no trials")
    if not all(isinstance(t, TrialMeasurement) for t in trials):
        raise TypeError("trials must be TrialMeasurement objects")
    groups: dict[tuple[str, int], dict[str, TrialMeasurement]] = {}
    seen_runs = set()
    for t in trials:
        key = (t.task_id, t.replicate)
        group = groups.setdefault(key, {})
        if t.arm in group:
            raise ValueError(f"duplicate arm for {key}")
        if t.run_ref in seen_runs:
            raise ValueError("one run reused for multiple arms")
        seen_runs.add(t.run_ref)
        group[t.arm] = t
    paired = []
    for key, members in sorted(groups.items()):
        if set(members) != ARMS:
            raise ValueError(f"incomplete triplet at {key}: {sorted(members)}")
        control = members["control"]
        for t in members.values():
            equal = (t.model_id, t.model_revision, t.document_sha256,
                     t.protocol_sha256, t.budget_tokens, t.scorer_ref)
            reference = (control.model_id, control.model_revision,
                         control.document_sha256, control.protocol_sha256,
                         control.budget_tokens, control.scorer_ref)
            if equal != reference:
                raise ValueError(f"confounded mismatched trial at {key}")
        paired.append({
            "task_id": key[0], "replicate": key[1],
            "treatment_minus_control": members["treatment"].score - control.score,
            "placebo_minus_control": members["placebo"].score - control.score,
            "treatment_minus_placebo": members["treatment"].score - members["placebo"].score,
            "treatment_latency_minus_control_ms": members["treatment"].latency_ms - control.latency_ms,
            "runs": {a: members[a].run_ref for a in sorted(ARMS)},
        })
    n = len(paired)
    means = {k: sum(p[k] for p in paired) / n for k in (
        "treatment_minus_control", "placebo_minus_control",
        "treatment_minus_placebo", "treatment_latency_minus_control_ms")}
    return {
        "schema": VERSION, "pairs": n,
        "status": "pilot_only" if n < min_pairs else "awaiting_independent_replication",
        "causal_learning_demonstrated": False,
        "mean_deltas": means, "paired_results": paired,
        "warnings": [
            "Input run references and scores are host assertions, not authenticated proof.",
            "Same-model/model-revision strings are not cryptographic model attestation.",
            "No controlled trial alone demonstrates durable learning without a changed artifact, holdouts and independent replication.",
        ],
    }
