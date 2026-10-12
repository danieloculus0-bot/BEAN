"""Evidence-gated dual-state reasoning for mutually exclusive hypotheses.

This models classical epistemic uncertainty, not quantum mechanics or neural
learning. Missing evidence never proves a negative. Conflicting records and
context-specific hypotheses are preserved. Conclusions are provisional and
do not authorize actions.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Optional

DUAL_STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS cognition_dual_cases (
    case_key TEXT PRIMARY KEY,
    hypothesis_a TEXT NOT NULL,
    hypothesis_b TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cognition_dual_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_key TEXT NOT NULL REFERENCES cognition_dual_cases(case_key),
    evidence_ref TEXT NOT NULL,
    source_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('a','b')),
    context TEXT NOT NULL DEFAULT '',
    observation TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(case_key, evidence_ref)
);
CREATE INDEX IF NOT EXISTS idx_dual_evidence_case_context
ON cognition_dual_evidence(case_key, context);
"""


def _required(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")
    return value.strip()


class DualStateReasoner:
    """Preserve alternatives until source-attributed and contextual evidence separates them.

    The default connection is BEAN's existing SQLite MemoryStore. An explicit
    connection permits isolated testing. This code does not modify canonical
    world claims, authenticate external sources, retrain models, or take actions.
    """

    def __init__(self, connection: Optional[sqlite3.Connection] = None):
        if connection is None:
            from bean.memory.store import get_store
            connection = get_store()._conn()
        self.db = connection
        self.db.executescript(DUAL_STATE_SCHEMA)
        self.db.commit()

    def open_case(self, case_key: str, hypothesis_a: str, hypothesis_b: str) -> dict:
        case_key = _required(case_key, "case_key")
        hypothesis_a = _required(hypothesis_a, "hypothesis_a")
        hypothesis_b = _required(hypothesis_b, "hypothesis_b")
        if hypothesis_a == hypothesis_b:
            raise ValueError("hypotheses must be distinct")
        prior = self.db.execute(
            "SELECT hypothesis_a, hypothesis_b FROM cognition_dual_cases WHERE case_key=?",
            (case_key,),
        ).fetchone()
        if prior:
            if tuple(prior) != (hypothesis_a, hypothesis_b):
                raise ValueError("existing case cannot silently redefine hypotheses")
        else:
            self.db.execute(
                "INSERT INTO cognition_dual_cases (case_key, hypothesis_a, hypothesis_b) VALUES (?,?,?)",
                (case_key, hypothesis_a, hypothesis_b),
            )
            self.db.commit()
        return self.evaluate(case_key)

    def add_evidence(
        self,
        case_key: str,
        *,
        evidence_ref: str,
        source_id: str,
        side: str,
        observation: str,
        context: Optional[str] = None,
    ) -> dict:
        case_key = _required(case_key, "case_key")
        evidence_ref = _required(evidence_ref, "evidence_ref")
        source_id = _required(source_id, "source_id")
        observation = _required(observation, "observation")
        if side not in ("a", "b"):
            raise ValueError("side must be 'a' or 'b'")
        context = "" if context is None else _required(context, "context")
        payload = json.dumps(
            [case_key, evidence_ref, source_id, side, observation, context],
            ensure_ascii=False, separators=(",", ":"),
        )
        checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if not self.db.execute(
            "SELECT 1 FROM cognition_dual_cases WHERE case_key=?", (case_key,),
        ).fetchone():
            raise KeyError(f"unknown dual-state case: {case_key}")
        prior = self.db.execute(
            "SELECT payload_sha256 FROM cognition_dual_evidence "
            "WHERE case_key=? AND evidence_ref=?", (case_key, evidence_ref),
        ).fetchone()
        if prior:
            if prior[0] != checksum:
                raise ValueError("evidence_ref already recorded with different content")
        else:
            self.db.execute(
                "INSERT INTO cognition_dual_evidence "
                "(case_key,evidence_ref,source_id,side,context,observation,payload_sha256) "
                "VALUES (?,?,?,?,?,?,?)",
                (case_key, evidence_ref, source_id, side, context, observation, checksum),
            )
            self.db.commit()
        return self.evaluate(case_key, context=context or None)

    def evaluate(self, case_key: str, *, context: Optional[str] = None,
                 min_independent_sources: int = 2) -> dict:
        case_key = _required(case_key, "case_key")
        if (not isinstance(min_independent_sources, int)
                or isinstance(min_independent_sources, bool)
                or min_independent_sources < 2):
            raise ValueError("require at least two independent sources")
        context = "" if context is None else _required(context, "context")
        row = self.db.execute(
            "SELECT hypothesis_a, hypothesis_b FROM cognition_dual_cases WHERE case_key=?",
            (case_key,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown dual-state case: {case_key}")
        observations = self.db.execute(
            "SELECT evidence_ref, source_id, side, observation, payload_sha256 "
            "FROM cognition_dual_evidence WHERE case_key=? AND context=? ORDER BY id",
            (case_key, context),
        ).fetchall()
        counts = {
            side: len({entry[1] for entry in observations if entry[2] == side})
            for side in ("a", "b")
        }
        any_contextual = self.db.execute(
            "SELECT 1 FROM cognition_dual_evidence WHERE case_key=? AND context<>'' LIMIT 1",
            (case_key,),
        ).fetchone() is not None
        if not observations and not context and any_contextual:
            status, selected, next_step = (
                "context_required", None,
                "Identify the current evidence-backed context before selecting a hypothesis.",
            )
        elif not observations:
            status, selected, next_step = (
                "unknown", None,
                "Gather direct, source-attributed evidence for either hypothesis.",
            )
        elif counts["a"] and counts["b"]:
            status, selected, next_step = (
                "contested", None,
                "Obtain an independently verifiable observation that distinguishes the claims.",
            )
        elif counts["a"] >= min_independent_sources:
            status, selected, next_step = (
                "supported_a", "a", "Continue falsification checks; support is provisional.",
            )
        elif counts["b"] >= min_independent_sources:
            status, selected, next_step = (
                "supported_b", "b", "Continue falsification checks; support is provisional.",
            )
        else:
            status, selected, next_step = (
                "insufficient_evidence", None,
                "Seek evidence from an independent origin, not a repeat of one source.",
            )
        return {
            "case_key": case_key,
            "hypotheses": {"a": row[0], "b": row[1]},
            "context": context or None,
            "status": status,
            "selected": selected,
            "independent_sources": counts,
            "evidence_count": len(observations),
            "evidence": [
                {"evidence_ref": e[0], "source_id": e[1], "side": e[2],
                 "observation": e[3], "payload_sha256": e[4]}
                for e in observations
            ],
            "next_evidence_needed": next_step,
            "action_authorized": False,
            "note": "Evidence sources are caller-attributed, not independently authenticated.",
        }

    def contexts(self, case_key: str) -> list[str]:
        case_key = _required(case_key, "case_key")
        if not self.db.execute(
            "SELECT 1 FROM cognition_dual_cases WHERE case_key=?", (case_key,),
        ).fetchone():
            raise KeyError(f"unknown dual-state case: {case_key}")
        return [row[0] for row in self.db.execute(
            "SELECT DISTINCT context FROM cognition_dual_evidence WHERE case_key=? "
            "AND context<>'' ORDER BY context", (case_key,),
        ).fetchall()]
