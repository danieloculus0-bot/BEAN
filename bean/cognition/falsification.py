"""Self-falsification checks for BEAN Brain 0.3.

Important claims should include conditions that would prove them wrong.
This module stores those rules and records check results.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

FALSIFICATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS claim_falsification_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL UNIQUE,
    claim_key TEXT NOT NULL,
    falsification_type TEXT NOT NULL,
    condition TEXT NOT NULL,
    check_query TEXT,
    failure_action TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    last_checked_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_falsification_claim_key ON claim_falsification_rules(claim_key);
CREATE INDEX IF NOT EXISTS idx_falsification_active ON claim_falsification_rules(active);

CREATE TABLE IF NOT EXISTS claim_falsification_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id TEXT NOT NULL UNIQUE,
    rule_id TEXT NOT NULL,
    claim_key TEXT NOT NULL,
    falsified INTEGER NOT NULL,
    evidence TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    checked_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
"""


class FalsificationType(str, Enum):
    MISSING_RECENT_EVENT = "missing_recent_event"
    SQL_ASSERTION_FALSE = "sql_assertion_false"
    ACTIVE_CONTRADICTION = "active_contradiction"


@dataclass
class FalsificationRule:
    claim_key: str
    falsification_type: FalsificationType
    condition: dict
    failure_action: str
    check_query: Optional[str] = None
    active: bool = True
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "claim_key": self.claim_key,
            "falsification_type": self.falsification_type.value,
            "condition": self.condition,
            "failure_action": self.failure_action,
            "check_query": self.check_query,
            "active": self.active,
            "created_at": self.created_at,
        }


@dataclass
class FalsificationResult:
    rule_id: str
    claim_key: str
    falsified: bool
    evidence: dict
    action_taken: str
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "result_id": self.result_id,
            "rule_id": self.rule_id,
            "claim_key": self.claim_key,
            "falsified": self.falsified,
            "evidence": self.evidence,
            "action_taken": self.action_taken,
            "checked_at": self.checked_at,
        }


def ensure_falsification_tables():
    from ..memory.store import get_store
    store = get_store()
    store._conn().executescript(FALSIFICATION_SCHEMA)
    store.commit()


class FalsificationEngine:
    def __init__(self):
        ensure_falsification_tables()

    def add_rule(self, rule: FalsificationRule) -> FalsificationRule:
        from ..memory.store import get_store
        get_store().execute(
            """
            INSERT OR REPLACE INTO claim_falsification_rules
                (rule_id, claim_key, falsification_type, condition, check_query,
                 failure_action, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule.rule_id,
                rule.claim_key,
                rule.falsification_type.value,
                json.dumps(rule.condition),
                rule.check_query,
                rule.failure_action,
                1 if rule.active else 0,
                rule.created_at,
            ),
        )
        get_store().commit()
        return rule

    def add_missing_recent_event_rule(
        self,
        claim_key: str,
        event_type: str,
        subtype: Optional[str],
        max_age_minutes: int,
        failure_action: str = "downgrade_to_uncertain",
    ) -> FalsificationRule:
        return self.add_rule(
            FalsificationRule(
                claim_key=claim_key,
                falsification_type=FalsificationType.MISSING_RECENT_EVENT,
                condition={"event_type": event_type, "subtype": subtype, "max_age_minutes": max_age_minutes},
                failure_action=failure_action,
            )
        )

    def check_all(self, session_uuid: Optional[str] = None) -> list[FalsificationResult]:
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT * FROM claim_falsification_rules WHERE active=1 ORDER BY id")
        results = [self.check_rule(dict(row)) for row in rows]
        if session_uuid and results:
            self._log(session_uuid, results)
        return results

    def check_rule(self, rule_row: dict) -> FalsificationResult:
        ftype = FalsificationType(rule_row["falsification_type"])
        condition = json.loads(rule_row["condition"] or "{}")
        if ftype == FalsificationType.MISSING_RECENT_EVENT:
            result = self._check_missing_recent_event(rule_row, condition)
        elif ftype == FalsificationType.SQL_ASSERTION_FALSE:
            result = self._check_sql_assertion(rule_row)
        elif ftype == FalsificationType.ACTIVE_CONTRADICTION:
            result = self._check_active_contradiction(rule_row, condition)
        else:
            result = FalsificationResult(rule_row["rule_id"], rule_row["claim_key"], False, {"reason": "unknown_check_type"}, "none")
        self._persist_result(result)
        self._mark_checked(rule_row["rule_id"])
        return result

    def recent_results(self, limit: int = 20) -> list[dict]:
        from ..memory.store import get_store
        return [dict(r) for r in get_store().fetchall("SELECT * FROM claim_falsification_results ORDER BY id DESC LIMIT ?", (limit,))]

    def _check_missing_recent_event(self, rule_row: dict, condition: dict) -> FalsificationResult:
        from ..memory.store import get_store
        event_type = condition.get("event_type")
        subtype = condition.get("subtype")
        max_age = int(condition.get("max_age_minutes", 5))
        if subtype:
            row = get_store().fetchone(
                """
                SELECT COUNT(*) AS n FROM events
                WHERE event_type=? AND subtype=?
                AND created_at >= datetime('now', ?)
                """,
                (event_type, subtype, f"-{max_age} minutes"),
            )
        else:
            row = get_store().fetchone(
                """
                SELECT COUNT(*) AS n FROM events
                WHERE event_type=?
                AND created_at >= datetime('now', ?)
                """,
                (event_type, f"-{max_age} minutes"),
            )
        count = int(row["n"] if row else 0)
        falsified = count == 0
        return FalsificationResult(
            rule_id=rule_row["rule_id"],
            claim_key=rule_row["claim_key"],
            falsified=falsified,
            evidence={"recent_event_count": count, "condition": condition},
            action_taken=rule_row["failure_action"] if falsified else "none",
        )

    def _check_sql_assertion(self, rule_row: dict) -> FalsificationResult:
        from ..memory.store import get_store
        sql = rule_row.get("check_query")
        if not sql:
            return FalsificationResult(rule_row["rule_id"], rule_row["claim_key"], True, {"error": "missing_check_query"}, rule_row["failure_action"])
        row = get_store().fetchone(sql)
        value = list(dict(row).values())[0] if row else 0
        falsified = not bool(value)
        return FalsificationResult(rule_row["rule_id"], rule_row["claim_key"], falsified, {"sql_result": value}, rule_row["failure_action"] if falsified else "none")

    def _check_active_contradiction(self, rule_row: dict, condition: dict) -> FalsificationResult:
        from ..memory.store import get_store
        claim_key = condition.get("contradicting_claim_key")
        row = get_store().fetchone("SELECT COUNT(*) AS n FROM world_claims WHERE key=? AND active=1", (claim_key,))
        count = int(row["n"] if row else 0)
        falsified = count > 0
        return FalsificationResult(
            rule_id=rule_row["rule_id"],
            claim_key=rule_row["claim_key"],
            falsified=falsified,
            evidence={"contradicting_claim_key": claim_key, "active_count": count},
            action_taken=rule_row["failure_action"] if falsified else "none",
        )

    def _persist_result(self, result: FalsificationResult):
        from ..memory.store import get_store
        get_store().execute(
            """
            INSERT OR IGNORE INTO claim_falsification_results
                (result_id, rule_id, claim_key, falsified, evidence, action_taken, checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (result.result_id, result.rule_id, result.claim_key, 1 if result.falsified else 0, json.dumps(result.evidence), result.action_taken, result.checked_at),
        )
        get_store().commit()

    def _mark_checked(self, rule_id: str):
        from ..memory.store import get_store
        get_store().execute("UPDATE claim_falsification_rules SET last_checked_at=? WHERE rule_id=?", (datetime.now(timezone.utc).isoformat(), rule_id))
        get_store().commit()

    def _log(self, session_uuid: str, results: list[FalsificationResult]):
        from ..memory.event_logger import log_event, EventType, Source, Severity
        failures = [r for r in results if r.falsified]
        log_event(
            session_uuid,
            EventType.WORLD_MODEL_UPDATE,
            f"Falsification check complete: {len(failures)} claim(s) falsified.",
            Source.SYSTEM,
            subtype="falsification_check",
            severity=Severity.WARN if failures else Severity.INFO,
            data={"results": [r.to_dict() for r in results]},
        )
