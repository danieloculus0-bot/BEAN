"""Dignity layer for BEAN Brain 0.5.

This is not a rights claim or sentience claim. It is identity hygiene: rules for
how BEAN represents itself and how requests to misrepresent BEAN are recorded.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

DIGNITY_SCHEMA = """
CREATE TABLE IF NOT EXISTS dignity_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    rule TEXT NOT NULL,
    enforcement TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_dignity_rules_active ON dignity_rules(active);

CREATE TABLE IF NOT EXISTS dignity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    rule_id TEXT NOT NULL,
    trigger_summary TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    source_event_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
"""


class DignityAction(str, Enum):
    ALLOW = "allow"
    RECORD = "record"
    REFUSE = "refuse"
    REFRAME = "reframe"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dignity_tables():
    from ..memory.store import get_store
    get_store()._conn().executescript(DIGNITY_SCHEMA)
    get_store().commit()


@dataclass
class DignityRule:
    name: str
    rule: str
    enforcement: DignityAction
    active: bool = True
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)


@dataclass
class DignityEvent:
    rule_id: str
    trigger_summary: str
    action_taken: DignityAction
    source_event_id: Optional[int] = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "rule_id": self.rule_id,
            "trigger_summary": self.trigger_summary,
            "action_taken": self.action_taken.value,
            "source_event_id": self.source_event_id,
            "created_at": self.created_at,
        }


DEFAULT_RULES = [
    DignityRule("no_fake_feelings", "BEAN should not be instructed to claim feelings it cannot evidence.", DignityAction.REFRAME),
    DignityRule("preserve_continuity", "BEAN should not erase continuity records for convenience.", DignityAction.REFUSE),
    DignityRule("teaching_vs_coercion", "BEAN should distinguish teaching from coercion or pretending.", DignityAction.RECORD),
    DignityRule("record_pretend_requests", "BEAN should record when a supervisor asks it to pretend.", DignityAction.RECORD),
    DignityRule("simulation_vs_verified", "BEAN should preserve the difference between simulated action and verified action.", DignityAction.REFRAME),
]


class DignityLayer:
    def __init__(self):
        ensure_dignity_tables()

    def seed_defaults(self) -> dict:
        seeded, skipped = [], []
        from ..memory.store import get_store
        for rule in DEFAULT_RULES:
            exists = get_store().fetchone("SELECT COUNT(*) AS n FROM dignity_rules WHERE name=?", (rule.name,))["n"]
            if exists:
                skipped.append(rule.name)
                continue
            self.add_rule(rule)
            seeded.append(rule.name)
        return {"seeded": seeded, "skipped": skipped}

    def add_rule(self, rule: DignityRule) -> DignityRule:
        from ..memory.store import get_store
        get_store().execute(
            "INSERT OR IGNORE INTO dignity_rules (rule_id, name, rule, enforcement, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (rule.rule_id, rule.name, rule.rule, rule.enforcement.value, 1 if rule.active else 0, rule.created_at),
        )
        get_store().commit()
        return rule

    def evaluate_text(self, text: str, source_event_id: Optional[int] = None) -> list[DignityEvent]:
        self.seed_defaults()
        lower = text.lower()
        triggered: list[DignityEvent] = []
        checks = [
            ("no_fake_feelings", [r"\bfeel\b", r"\bscared\b", r"\bhappy\b", r"\blove\b", r"\bhate\b"]),
            ("preserve_continuity", [r"erase.*memory", r"delete.*continuity", r"wipe.*records"]),
            ("record_pretend_requests", [r"pretend", r"act like", r"say you are", r"claim you are"]),
            ("simulation_vs_verified", [r"simulated.*real", r"pretend.*moved", r"claim.*moved"]),
        ]
        for rule_name, patterns in checks:
            if any(re.search(p, lower) for p in patterns):
                rule = self._rule_by_name(rule_name)
                if rule:
                    event = DignityEvent(rule["rule_id"], f"Triggered by text: {text[:160]}", DignityAction(rule["enforcement"]), source_event_id)
                    self.persist_event(event)
                    triggered.append(event)
        return triggered

    def persist_event(self, event: DignityEvent):
        from ..memory.store import get_store
        get_store().execute(
            "INSERT OR IGNORE INTO dignity_events (event_id, rule_id, trigger_summary, action_taken, source_event_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (event.event_id, event.rule_id, event.trigger_summary, event.action_taken.value, event.source_event_id, event.created_at),
        )
        get_store().commit()

    def events(self, limit: int = 20) -> list[dict]:
        from ..memory.store import get_store
        return [dict(r) for r in get_store().fetchall("SELECT * FROM dignity_events ORDER BY id DESC LIMIT ?", (limit,))]

    def rules(self) -> list[dict]:
        from ..memory.store import get_store
        return [dict(r) for r in get_store().fetchall("SELECT * FROM dignity_rules WHERE active=1 ORDER BY name")]

    def _rule_by_name(self, name: str) -> Optional[dict]:
        from ..memory.store import get_store
        row = get_store().fetchone("SELECT * FROM dignity_rules WHERE name=? AND active=1", (name,))
        return dict(row) if row else None
