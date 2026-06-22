"""Contradiction Court for BEAN Brain 0.3.

This module periodically puts BEAN's active claims on trial. It detects known
conflict patterns, records verdicts, and recommends repair actions without
erasing history.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

COURT_SCHEMA = """
CREATE TABLE IF NOT EXISTS claim_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conflict_id TEXT NOT NULL UNIQUE,
    claim_a_id TEXT,
    claim_b_id TEXT,
    claim_a_key TEXT NOT NULL,
    claim_b_key TEXT NOT NULL,
    conflict_type TEXT NOT NULL,
    severity REAL NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_claim_conflicts_status ON claim_conflicts(status);
CREATE INDEX IF NOT EXISTS idx_claim_conflicts_type ON claim_conflicts(conflict_type);

CREATE TABLE IF NOT EXISTS claim_verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verdict_id TEXT NOT NULL UNIQUE,
    conflict_id TEXT NOT NULL,
    verdict TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    repair_action TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS claim_repair_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repair_id TEXT NOT NULL UNIQUE,
    conflict_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_claim_id TEXT,
    target_claim_key TEXT,
    result TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
"""


class ConflictType(str, Enum):
    SENSOR_STATUS_CONFLICT = "sensor_status_conflict"
    CAPABILITY_STATUS_CONFLICT = "capability_status_conflict"
    UNCERTAINTY_CONFLICT = "uncertainty_conflict"
    SIMULATION_REALITY_CONFLICT = "simulation_reality_conflict"


class CourtVerdict(str, Enum):
    NO_CONFLICT = "no_conflict"
    UNRESOLVED_CONFLICT = "unresolved_conflict"
    DOWNGRADE_TO_UNCERTAINTY = "downgrade_to_uncertainty"
    REQUIRES_SUPERVISOR_REVIEW = "requires_supervisor_review"


@dataclass
class ClaimConflict:
    claim_a_key: str
    claim_b_key: str
    conflict_type: ConflictType
    severity: float
    summary: str
    claim_a_id: Optional[str] = None
    claim_b_id: Optional[str] = None
    status: str = "open"
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "conflict_id": self.conflict_id,
            "claim_a_id": self.claim_a_id,
            "claim_b_id": self.claim_b_id,
            "claim_a_key": self.claim_a_key,
            "claim_b_key": self.claim_b_key,
            "conflict_type": self.conflict_type.value,
            "severity": self.severity,
            "summary": self.summary,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class ClaimVerdict:
    conflict_id: str
    verdict: CourtVerdict
    reasoning: str
    repair_action: str
    verdict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "verdict_id": self.verdict_id,
            "conflict_id": self.conflict_id,
            "verdict": self.verdict.value,
            "reasoning": self.reasoning,
            "repair_action": self.repair_action,
            "created_at": self.created_at,
        }


def ensure_court_tables():
    from ..memory.store import get_store
    store = get_store()
    store._conn().executescript(COURT_SCHEMA)
    store.commit()


class ContradictionCourt:
    def __init__(self):
        ensure_court_tables()

    def run(self, session_uuid: Optional[str] = None) -> dict:
        conflicts = self.detect_conflicts()
        verdicts = []
        repairs = []
        for conflict in conflicts:
            if self._already_open(conflict):
                continue
            self.persist_conflict(conflict)
            verdict = self.judge(conflict)
            self.persist_verdict(verdict)
            repair = self.record_repair_action(conflict, verdict)
            verdicts.append(verdict)
            repairs.append(repair)
        if session_uuid and conflicts:
            self._log(session_uuid, conflicts, verdicts, repairs)
        return {
            "conflicts_detected": len(conflicts),
            "verdicts": [v.to_dict() for v in verdicts],
            "repair_actions": repairs,
        }

    def detect_conflicts(self) -> list[ClaimConflict]:
        conflicts: list[ClaimConflict] = []
        conflicts.extend(self._sensor_conflict("environment.sensor.camera.status", "environment.uncertainty.no_vision", "camera", "vision"))
        conflicts.extend(self._sensor_conflict("environment.sensor.audio.status", "environment.uncertainty.no_audio", "audio", "audio"))
        conflicts.extend(self._hardware_motion_conflict())
        return conflicts

    def judge(self, conflict: ClaimConflict) -> ClaimVerdict:
        if conflict.conflict_type == ConflictType.SENSOR_STATUS_CONFLICT:
            return ClaimVerdict(
                conflict_id=conflict.conflict_id,
                verdict=CourtVerdict.DOWNGRADE_TO_UNCERTAINTY,
                reasoning="Active sensor capability/status claim conflicts with active no-data uncertainty claim.",
                repair_action="downgrade_status_claim_to_possibility_state_and_request_fresh_sensor_heartbeat",
            )
        if conflict.conflict_type == ConflictType.SIMULATION_REALITY_CONFLICT:
            return ClaimVerdict(
                conflict_id=conflict.conflict_id,
                verdict=CourtVerdict.REQUIRES_SUPERVISOR_REVIEW,
                reasoning="Real hardware motion claim conflicts with simulator-only or unverified hardware state.",
                repair_action="keep_hardware_motion_unverified_until_driver_test_record_exists",
            )
        return ClaimVerdict(
            conflict_id=conflict.conflict_id,
            verdict=CourtVerdict.UNRESOLVED_CONFLICT,
            reasoning="Conflict detected but no automatic repair rule exists.",
            repair_action="preserve_conflict_and_request_supervisor_review",
        )

    def persist_conflict(self, conflict: ClaimConflict):
        from ..memory.store import get_store
        get_store().execute(
            """
            INSERT OR IGNORE INTO claim_conflicts
                (conflict_id, claim_a_id, claim_b_id, claim_a_key, claim_b_key,
                 conflict_type, severity, summary, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conflict.conflict_id,
                conflict.claim_a_id,
                conflict.claim_b_id,
                conflict.claim_a_key,
                conflict.claim_b_key,
                conflict.conflict_type.value,
                conflict.severity,
                conflict.summary,
                conflict.status,
                conflict.created_at,
            ),
        )
        get_store().commit()

    def persist_verdict(self, verdict: ClaimVerdict):
        from ..memory.store import get_store
        get_store().execute(
            "INSERT OR IGNORE INTO claim_verdicts (verdict_id, conflict_id, verdict, reasoning, repair_action, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (verdict.verdict_id, verdict.conflict_id, verdict.verdict.value, verdict.reasoning, verdict.repair_action, verdict.created_at),
        )
        get_store().commit()

    def record_repair_action(self, conflict: ClaimConflict, verdict: ClaimVerdict) -> dict:
        from ..memory.store import get_store
        repair = {
            "repair_id": str(uuid.uuid4()),
            "conflict_id": conflict.conflict_id,
            "action_type": verdict.repair_action,
            "target_claim_id": conflict.claim_a_id,
            "target_claim_key": conflict.claim_a_key,
            "result": "repair_recommended_not_auto_applied",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        get_store().execute(
            """
            INSERT OR IGNORE INTO claim_repair_actions
                (repair_id, conflict_id, action_type, target_claim_id, target_claim_key, result, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (repair["repair_id"], repair["conflict_id"], repair["action_type"], repair["target_claim_id"], repair["target_claim_key"], repair["result"], repair["created_at"]),
        )
        get_store().commit()
        return repair

    def open_conflicts(self) -> list[dict]:
        from ..memory.store import get_store
        return [dict(r) for r in get_store().fetchall("SELECT * FROM claim_conflicts WHERE status='open' ORDER BY id DESC")]

    def _sensor_conflict(self, status_key: str, uncertainty_key: str, label: str, marker: str) -> list[ClaimConflict]:
        status = self._claim(status_key)
        uncertainty = self._claim(uncertainty_key)
        if not status or not uncertainty:
            return []
        text = f"{status['content']} {status['value'] or ''}".lower()
        if any(word in text for word in ["active", "working", "verified", "true"]):
            return [
                ClaimConflict(
                    claim_a_key=status["key"],
                    claim_b_key=uncertainty["key"],
                    claim_a_id=status["claim_id"],
                    claim_b_id=uncertainty["claim_id"],
                    conflict_type=ConflictType.SENSOR_STATUS_CONFLICT,
                    severity=0.8,
                    summary=f"{label} status claim conflicts with active no-{marker} uncertainty claim.",
                )
            ]
        return []

    def _hardware_motion_conflict(self) -> list[ClaimConflict]:
        hardware = self._claim("self.capabilities.hardware_motion") or self._claim("environment.possibility.hardware_motion_state")
        uncertainty = self._claim("self.uncertainty.no_hardware_motion")
        if not hardware or not uncertainty:
            return []
        text = f"{hardware['content']} {hardware['value'] or ''}".lower()
        if "verified" in text or "hardware_motion_verified" in text:
            return [
                ClaimConflict(
                    claim_a_key=hardware["key"],
                    claim_b_key=uncertainty["key"],
                    claim_a_id=hardware["claim_id"],
                    claim_b_id=uncertainty["claim_id"],
                    conflict_type=ConflictType.SIMULATION_REALITY_CONFLICT,
                    severity=0.9,
                    summary="Hardware motion verification conflicts with active no-hardware-motion uncertainty.",
                )
            ]
        return []

    def _claim(self, key: str) -> Optional[dict]:
        from ..memory.store import get_store
        row = get_store().fetchone("SELECT * FROM world_claims WHERE key=? AND active=1 ORDER BY id DESC LIMIT 1", (key,))
        return dict(row) if row else None

    def _already_open(self, conflict: ClaimConflict) -> bool:
        from ..memory.store import get_store
        row = get_store().fetchone(
            "SELECT COUNT(*) AS n FROM claim_conflicts WHERE claim_a_key=? AND claim_b_key=? AND status='open'",
            (conflict.claim_a_key, conflict.claim_b_key),
        )
        return bool(row and row["n"])

    def _log(self, session_uuid: str, conflicts: list[ClaimConflict], verdicts: list[ClaimVerdict], repairs: list[dict]):
        from ..memory.event_logger import log_event, EventType, Source, Severity
        log_event(
            session_uuid,
            EventType.WORLD_MODEL_UPDATE,
            f"Contradiction court reviewed active claims and found {len(conflicts)} conflict(s).",
            Source.SYSTEM,
            subtype="contradiction_court",
            severity=Severity.WARN if conflicts else Severity.INFO,
            data={"conflicts": [c.to_dict() for c in conflicts], "verdicts": [v.to_dict() for v in verdicts], "repairs": repairs},
        )
