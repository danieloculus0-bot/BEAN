"""Host-neutral evidence-to-memory loop for BEAN Core.

Contract: the host supplies source claims, provenance, and *separate* verifier
attestations. BEAN persists all observations and resolves only a round with two
different, agreeing verified origins. Unverified copies or LLM outputs do not
vote. Every subsequent round can challenge prior conclusions.

This is a proposal/knowledge interface: no network retrieval, commands,
motion, trading, or unreviewed self-modification. An origin is a host
assertion, not authenticated ownership. A verified flag does not prove truth.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from bean.cognition.epistemic_guard import CandidateClaim, EpistemicGuard
from bean.cognition.uncertainty_garden import UncertaintyGarden, UncertaintyRecord
from bean.memory.event_logger import EventType, Source

if TYPE_CHECKING:
    from .reasoning_layer import BeanReasoningLayer

KEY = re.compile(r"^[a-z][a-z0-9_.-]{1,79}$")
SCHEMA = """
CREATE TABLE IF NOT EXISTS bridge_evidence_rounds (
  round_id TEXT PRIMARY KEY, claim_key TEXT NOT NULL, question TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('open','closed')),
  uncertainty_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bridge_evidence_inputs (
  record_id TEXT PRIMARY KEY, round_id TEXT NOT NULL,
  origin TEXT NOT NULL, source_ref TEXT NOT NULL,
  value TEXT NOT NULL, verified INTEGER NOT NULL CHECK(verified IN (0,1)),
  verification_ref TEXT, observed_at TEXT NOT NULL,
  FOREIGN KEY(round_id) REFERENCES bridge_evidence_rounds(round_id),
  UNIQUE(round_id, source_ref)
);
CREATE TABLE IF NOT EXISTS bridge_evidence_findings (
  finding_id INTEGER PRIMARY KEY AUTOINCREMENT,
  round_id TEXT NOT NULL UNIQUE,
  claim_key TEXT NOT NULL,
  status TEXT NOT NULL,
  value TEXT, independent_origins INTEGER NOT NULL,
  evidence_json TEXT NOT NULL,
  previous_value TEXT,
  FOREIGN KEY(round_id) REFERENCES bridge_evidence_rounds(round_id)
);
CREATE INDEX IF NOT EXISTS bridge_findings_claim
ON bridge_evidence_findings(claim_key,finding_id);
"""


def _key(value: str, name: str) -> str:
    if not isinstance(value, str) or not KEY.fullmatch(value):
        raise ValueError(f"invalid {name}")
    return value


def _text(value: str, name: str, limit: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"invalid {name}")
    return value


def _utc(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("observed_at needs an explicit timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            raise ValueError("timezone required")
    except (ValueError, TypeError) as exc:
        raise ValueError("observed_at needs an explicit timezone") from exc
    return parsed.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class SourceClaim:
    record_id: str
    round_id: str
    origin: str
    source_ref: str
    value: str
    verified: bool
    verification_ref: str | None
    observed_at: str

    def __post_init__(self):
        _key(self.record_id, "record_id")
        _key(self.round_id, "round_id")
        _key(self.origin, "origin")
        _text(self.source_ref, "source_ref", 250)
        _text(self.value, "claim_value")
        if type(self.verified) is not bool:
            raise ValueError("verified must be explicitly boolean")
        if self.verified:
            _text(self.verification_ref, "verification_ref", 250)
            if self.verification_ref == self.source_ref:
                raise ValueError("verification must be independently referenced")
        elif self.verification_ref is not None:
            raise ValueError("unverified observation cannot have verification_ref")
        _utc(self.observed_at)


class EvidenceBridge:
    """Process-bounded interface to the actual BEAN memory and cognition layer.

    The host owns the session and closes it after use. The journal is persisted
    in that session's SQLite database. Do not share a Core MemoryStore singleton
    among parallel hosts.
    """

    def __init__(self, layer: "BeanReasoningLayer", *, min_origins: int = 2):
        if type(min_origins) is not int or not 2 <= min_origins <= 8:
            raise ValueError("independent origin threshold must be 2..8")
        self.layer = layer
        layer._ensure_open()
        self.db = layer.store._conn()
        self.db.executescript(SCHEMA)
        self.db.commit()
        self.garden = UncertaintyGarden()
        self.guard = EpistemicGuard()
        self.min_origins = min_origins

    def start(self, round_id: str, claim_key: str, question: str) -> dict:
        self.layer._ensure_open()
        _key(round_id, "round_id")
        _key(claim_key, "claim_key")
        _text(question, "question")
        row = self.db.execute(
            "SELECT * FROM bridge_evidence_rounds WHERE round_id=?", (round_id,)
        ).fetchone()
        if row:
            if row["claim_key"] != claim_key or row["question"] != question:
                raise ValueError("conflicting round identity")
            return {"round_id": round_id, "state": row["state"],
                    "uncertainty_id": row["uncertainty_id"], "new": False}
        uncertainty = self.garden.plant(
            UncertaintyRecord(
                question=question,
                what_would_resolve_it="Two independently verified, differently originated reports agree without contradiction",
                significance=0.6,
            ),
            [("Candidate explanation supported", 0.45),
             ("Candidate explanation refuted", 0.45),
             ("Insufficient source evidence", 0.1)],
        )
        self.db.execute(
            "INSERT INTO bridge_evidence_rounds(round_id,claim_key,question,state,uncertainty_id)"
            " VALUES(?,?,?,'open',?)",
            (round_id, claim_key, question, uncertainty.uncertainty_id),
        )
        self.db.commit()
        self.layer.record_event(
            "Evidence question opened", event_type=EventType.CURIOSITY,
            source=Source.SYSTEM, subtype="bridge_evidence",
            data={"round_id": round_id, "claim_key": claim_key, "question": question},
        )
        return {"round_id": round_id, "state": "open",
                "uncertainty_id": uncertainty.uncertainty_id, "new": True}

    def observe(self, item: SourceClaim) -> bool:
        self.layer._ensure_open()
        if not isinstance(item, SourceClaim):
            raise TypeError("must provide SourceClaim, not a model output dictionary")
        r = self.db.execute(
            "SELECT claim_key,state FROM bridge_evidence_rounds WHERE round_id=?",
            (item.round_id,),
        ).fetchone()
        if not r:
            raise ValueError("round not started")
        expected = (
            item.round_id, item.origin, item.source_ref, item.value,
            int(item.verified), item.verification_ref, _utc(item.observed_at),
        )
        existing = self.db.execute(
            "SELECT round_id,origin,source_ref,value,verified,verification_ref,observed_at "
            "FROM bridge_evidence_inputs WHERE record_id=?", (item.record_id,)
        ).fetchone()
        if existing:
            if tuple(existing) == expected:
                return False
            raise ValueError("same record_id with different evidence")
        if r["state"] != "open":
            raise ValueError("cannot append evidence to a finalized round")
        try:
            self.db.execute(
                "INSERT INTO bridge_evidence_inputs("
                "record_id,round_id,origin,source_ref,value,verified,verification_ref,observed_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (item.record_id, *expected),
            )
        except Exception as exc:
            # Preserve SQLite uniqueness checks instead of silently treating
            # a second record ID with the same source citation as independent.
            self.db.rollback()
            raise ValueError("duplicate or invalid source evidence") from exc
        self.db.commit()
        self.layer.record_event(
            "External source claim recorded", event_type=EventType.OBSERVATION,
            source=Source.SYSTEM, subtype="bridge_evidence",
            data={"round_id": item.round_id, "record_id": item.record_id,
                  "origin": item.origin, "source_ref": item.source_ref,
                  "host_verified": item.verified,
                  "verification_ref": item.verification_ref},
        )
        return True

    def finalize(self, round_id: str) -> dict:
        self.layer._ensure_open()
        _key(round_id, "round_id")
        round_row = self.db.execute(
            "SELECT * FROM bridge_evidence_rounds WHERE round_id=?", (round_id,)
        ).fetchone()
        if not round_row:
            raise ValueError("round not started")
        finding = self.db.execute(
            "SELECT * FROM bridge_evidence_findings WHERE round_id=?", (round_id,)
        ).fetchone()
        if finding:
            return self._finding(finding)
        data = self.db.execute(
            "SELECT * FROM bridge_evidence_inputs WHERE round_id=? ORDER BY record_id",
            (round_id,),
        ).fetchall()
        by_origin: dict[str, set[str]] = {}
        refs = []
        for row in data:
            if row["verified"]:
                by_origin.setdefault(row["origin"], set()).add(row["value"])
                refs.append({"origin": row["origin"], "source_ref": row["source_ref"],
                             "verification_ref": row["verification_ref"],
                             "value": row["value"]})
        vals = {value for values in by_origin.values() for value in values}
        previous = self.current(round_row["claim_key"])
        latest = previous["value"] if previous else None
        if len(vals) > 1:
            status, value = "contested", None
        elif len(by_origin) < self.min_origins:
            status, value = "insufficient", None
        else:
            value = next(iter(vals))
            status = "reaffirmed" if value == latest else "revised" if latest is not None else "confirmed"
        self.db.execute(
            "INSERT INTO bridge_evidence_findings("
            "round_id,claim_key,status,value,independent_origins,evidence_json,previous_value)"
            " VALUES(?,?,?,?,?,?,?)",
            (round_id, round_row["claim_key"], status, value,
             len(by_origin), json.dumps(refs, sort_keys=True), latest),
        )
        self.db.execute(
            "UPDATE bridge_evidence_rounds SET state='closed' WHERE round_id=?",
            (round_id,),
        )
        self.db.commit()
        if value is not None:
            # Verified means attested by the host, not authenticated factual truth.
            # Core's EpistemicGuard records this distinction and never actuates.
            self.guard.audit(CandidateClaim(
                key=f"external.research.{round_row['claim_key']}",
                content=f"Host-attested sources agree on {round_row['claim_key']}: {value}",
                source_type="host_attested",
                source_ref=f"evidence_round:{round_id}",
                confidence=min(0.99, len(by_origin) / (len(by_origin) + 1)),
                evidence=[x["verification_ref"] for x in refs],
                falsification_path="Open a new round with independently verified contrary evidence",
            ))
            options = self.garden.options(round_row["uncertainty_id"])
            if options:
                self.garden.resolve(
                    round_row["uncertainty_id"], options[0]["option_id"],
                    "Host-confirmed distinct sources agreed; evidence remains revisable",
                )
        self.layer.record_event(
            "Evidence round evaluated", event_type=EventType.WORLD_MODEL_UPDATE,
            source=Source.SYSTEM, subtype="bridge_evidence",
            data={"round_id": round_id, "claim_key": round_row["claim_key"],
                  "status": status, "distinct_origins": len(by_origin),
                  "proposed_value": value, "previous_value": latest},
        )
        return self._finding(self.db.execute(
            "SELECT * FROM bridge_evidence_findings WHERE round_id=?", (round_id,)
        ).fetchone())

    @staticmethod
    def _finding(row) -> dict:
        return {
            "round_id": row["round_id"], "claim_key": row["claim_key"],
            "status": row["status"], "value": row["value"],
            "previous_value": row["previous_value"],
            "distinct_origins": row["independent_origins"],
            "evidence": json.loads(row["evidence_json"]),
            "execution_permission": "none",
        }

    def current(self, claim_key: str) -> dict | None:
        self.layer._ensure_open()
        _key(claim_key, "claim_key")
        row = self.db.execute(
            "SELECT * FROM bridge_evidence_findings WHERE claim_key=? "
            "ORDER BY finding_id DESC LIMIT 1", (claim_key,),
        ).fetchone()
        if row is None or row["status"] not in {"confirmed", "revised", "reaffirmed"}:
            return None  # New conflicting evidence makes previous result non-current.
        return self._finding(row)

    def history(self, claim_key: str) -> list[dict]:
        self.layer._ensure_open()
        _key(claim_key, "claim_key")
        return [self._finding(r) for r in self.db.execute(
            "SELECT * FROM bridge_evidence_findings WHERE claim_key=? "
            "ORDER BY finding_id", (claim_key,),
        ).fetchall()]

    def pending(self) -> list[dict]:
        self.layer._ensure_open()
        return [dict(r) for r in self.db.execute(
            "SELECT round_id,claim_key,question,uncertainty_id FROM bridge_evidence_rounds "
            "WHERE state='open' ORDER BY rowid"
        ).fetchall()]
