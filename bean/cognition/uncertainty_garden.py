"""Uncertainty Garden for BEAN Brain 0.4.

The garden expands possibility states into explicit unresolved questions with
competing interpretations, evidence for/against, decay, review timing, and
resolution paths.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

UNCERTAINTY_SCHEMA = """
CREATE TABLE IF NOT EXISTS uncertainty_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uncertainty_id TEXT NOT NULL UNIQUE,
    question TEXT NOT NULL,
    significance REAL NOT NULL DEFAULT 0.5,
    status TEXT NOT NULL DEFAULT 'open',
    what_would_resolve_it TEXT NOT NULL,
    decay_rate REAL NOT NULL DEFAULT 0.01,
    last_reviewed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_uncertainty_status ON uncertainty_records(status);

CREATE TABLE IF NOT EXISTS uncertainty_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    option_id TEXT NOT NULL UNIQUE,
    uncertainty_id TEXT NOT NULL,
    interpretation TEXT NOT NULL,
    weight REAL NOT NULL,
    evidence_for TEXT NOT NULL DEFAULT '[]',
    evidence_against TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_uncertainty_options_uncertainty ON uncertainty_options(uncertainty_id);

CREATE TABLE IF NOT EXISTS uncertainty_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL UNIQUE,
    uncertainty_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    options_snapshot TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
"""


class UncertaintyStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DORMANT = "dormant"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_uncertainty_tables():
    from ..memory.store import get_store
    get_store()._conn().executescript(UNCERTAINTY_SCHEMA)
    get_store().commit()


@dataclass
class UncertaintyRecord:
    question: str
    what_would_resolve_it: str
    significance: float = 0.5
    decay_rate: float = 0.01
    status: UncertaintyStatus = UncertaintyStatus.OPEN
    uncertainty_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {
            "uncertainty_id": self.uncertainty_id,
            "question": self.question,
            "significance": self.significance,
            "status": self.status.value,
            "what_would_resolve_it": self.what_would_resolve_it,
            "decay_rate": self.decay_rate,
            "created_at": self.created_at,
        }


@dataclass
class UncertaintyOption:
    uncertainty_id: str
    interpretation: str
    weight: float
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)
    option_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {
            "option_id": self.option_id,
            "uncertainty_id": self.uncertainty_id,
            "interpretation": self.interpretation,
            "weight": self.weight,
            "evidence_for": self.evidence_for,
            "evidence_against": self.evidence_against,
            "created_at": self.created_at,
        }


class UncertaintyGarden:
    def __init__(self):
        ensure_uncertainty_tables()

    def plant(self, record: UncertaintyRecord, options: list[tuple[str, float]]) -> UncertaintyRecord:
        from ..memory.store import get_store
        get_store().execute(
            """
            INSERT OR IGNORE INTO uncertainty_records
                (uncertainty_id, question, significance, status, what_would_resolve_it, decay_rate, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (record.uncertainty_id, record.question, record.significance, record.status.value, record.what_would_resolve_it, record.decay_rate, record.created_at),
        )
        for interpretation, weight in options:
            opt = UncertaintyOption(record.uncertainty_id, interpretation, weight)
            self._insert_option(opt)
        get_store().commit()
        return record

    def add_evidence(self, uncertainty_id: str, option_id: str, evidence: str, supports: bool = True, weight_delta: float = 0.1):
        from ..memory.store import get_store
        row = get_store().fetchone("SELECT * FROM uncertainty_options WHERE option_id=?", (option_id,))
        if not row:
            return False
        e_for = json.loads(row["evidence_for"] or "[]")
        e_against = json.loads(row["evidence_against"] or "[]")
        weight = float(row["weight"])
        if supports:
            e_for.append(evidence)
            weight += abs(weight_delta)
        else:
            e_against.append(evidence)
            weight -= abs(weight_delta)
        get_store().execute(
            "UPDATE uncertainty_options SET evidence_for=?, evidence_against=?, weight=? WHERE option_id=?",
            (json.dumps(e_for), json.dumps(e_against), max(0.0, weight), option_id),
        )
        get_store().commit()
        self.normalize(uncertainty_id)
        return True

    def normalize(self, uncertainty_id: str):
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT option_id, weight FROM uncertainty_options WHERE uncertainty_id=?", (uncertainty_id,))
        total = sum(max(0.0, float(r["weight"])) for r in rows)
        if total <= 0 and rows:
            each = 1.0 / len(rows)
            for r in rows:
                get_store().execute("UPDATE uncertainty_options SET weight=? WHERE option_id=?", (each, r["option_id"]))
        elif total > 0:
            for r in rows:
                get_store().execute("UPDATE uncertainty_options SET weight=? WHERE option_id=?", (max(0.0, float(r["weight"])) / total, r["option_id"]))
        get_store().commit()

    def review(self, uncertainty_id: str) -> dict:
        from ..memory.store import get_store
        options = self.options(uncertainty_id)
        dominant = max(options, key=lambda o: o["weight"], default=None)
        summary = "No options available."
        if dominant:
            summary = f"Dominant interpretation is '{dominant['interpretation']}' at {dominant['weight']:.3f}, but uncertainty remains unless resolved."
        review = {"review_id": str(uuid.uuid4()), "uncertainty_id": uncertainty_id, "summary": summary, "options_snapshot": options, "created_at": _now()}
        get_store().execute(
            "INSERT INTO uncertainty_reviews (review_id, uncertainty_id, summary, options_snapshot, created_at) VALUES (?, ?, ?, ?, ?)",
            (review["review_id"], uncertainty_id, summary, json.dumps(options), review["created_at"]),
        )
        get_store().execute("UPDATE uncertainty_records SET last_reviewed_at=? WHERE uncertainty_id=?", (review["created_at"], uncertainty_id))
        get_store().commit()
        return review

    def resolve(self, uncertainty_id: str, selected_option_id: str, reason: str) -> bool:
        from ..memory.store import get_store
        row = get_store().fetchone("SELECT * FROM uncertainty_options WHERE option_id=? AND uncertainty_id=?", (selected_option_id, uncertainty_id))
        if not row:
            return False
        get_store().execute("UPDATE uncertainty_records SET status='resolved', last_reviewed_at=? WHERE uncertainty_id=?", (_now(), uncertainty_id))
        get_store().execute("UPDATE uncertainty_options SET weight=CASE WHEN option_id=? THEN 1.0 ELSE 0.0 END WHERE uncertainty_id=?", (selected_option_id, uncertainty_id))
        get_store().execute(
            "INSERT INTO uncertainty_reviews (review_id, uncertainty_id, summary, options_snapshot, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), uncertainty_id, f"Resolved to {row['interpretation']}: {reason}", json.dumps(self.options(uncertainty_id)), _now()),
        )
        get_store().commit()
        return True

    def open_uncertainties(self) -> list[dict]:
        from ..memory.store import get_store
        return [dict(r) for r in get_store().fetchall("SELECT * FROM uncertainty_records WHERE status='open' ORDER BY significance DESC, id DESC")]

    def options(self, uncertainty_id: str) -> list[dict]:
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT * FROM uncertainty_options WHERE uncertainty_id=? ORDER BY weight DESC", (uncertainty_id,))
        out = []
        for r in rows:
            d = dict(r)
            d["evidence_for"] = json.loads(d.get("evidence_for") or "[]")
            d["evidence_against"] = json.loads(d.get("evidence_against") or "[]")
            out.append(d)
        return out

    def _insert_option(self, option: UncertaintyOption):
        from ..memory.store import get_store
        get_store().execute(
            """
            INSERT OR IGNORE INTO uncertainty_options
                (option_id, uncertainty_id, interpretation, weight, evidence_for, evidence_against, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (option.option_id, option.uncertainty_id, option.interpretation, option.weight, json.dumps(option.evidence_for), json.dumps(option.evidence_against), option.created_at),
        )
