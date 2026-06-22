"""Inner Weather for BEAN Brain 0.5.

Inner weather is a machine-native pressure report, not emotion. It summarizes
continuity, uncertainty, novelty, trust, risk, curiosity, resource, and coherence
pressure from records.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

INNER_WEATHER_SCHEMA = """
CREATE TABLE IF NOT EXISTS inner_weather_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    continuity_pressure REAL NOT NULL,
    uncertainty_pressure REAL NOT NULL,
    novelty_pressure REAL NOT NULL,
    trust_pressure REAL NOT NULL,
    risk_pressure REAL NOT NULL,
    curiosity_pressure REAL NOT NULL,
    resource_pressure REAL NOT NULL,
    coherence_pressure REAL NOT NULL,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_inner_weather_session ON inner_weather_reports(session_uuid);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def ensure_inner_weather_table():
    from ..memory.store import get_store
    get_store()._conn().executescript(INNER_WEATHER_SCHEMA)
    get_store().commit()


@dataclass
class InnerWeatherReport:
    session_uuid: str
    continuity_pressure: float
    uncertainty_pressure: float
    novelty_pressure: float
    trust_pressure: float
    risk_pressure: float
    curiosity_pressure: float
    resource_pressure: float
    coherence_pressure: float
    summary: str
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class InnerWeatherEngine:
    def __init__(self):
        ensure_inner_weather_table()

    def generate(self, session_uuid: str) -> InnerWeatherReport:
        pressures = {
            "continuity_pressure": self._continuity_pressure(),
            "uncertainty_pressure": self._uncertainty_pressure(),
            "novelty_pressure": self._novelty_pressure(session_uuid),
            "trust_pressure": self._trust_pressure(),
            "risk_pressure": self._risk_pressure(),
            "curiosity_pressure": self._curiosity_pressure(),
            "resource_pressure": self._resource_pressure(),
            "coherence_pressure": self._coherence_pressure(),
        }
        summary = self._summary(pressures)
        report = InnerWeatherReport(session_uuid=session_uuid, summary=summary, **pressures)
        self.persist(report)
        return report

    def persist(self, report: InnerWeatherReport):
        from ..memory.store import get_store
        get_store().execute(
            """
            INSERT INTO inner_weather_reports
                (report_id, session_uuid, continuity_pressure, uncertainty_pressure,
                 novelty_pressure, trust_pressure, risk_pressure, curiosity_pressure,
                 resource_pressure, coherence_pressure, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.report_id,
                report.session_uuid,
                report.continuity_pressure,
                report.uncertainty_pressure,
                report.novelty_pressure,
                report.trust_pressure,
                report.risk_pressure,
                report.curiosity_pressure,
                report.resource_pressure,
                report.coherence_pressure,
                report.summary,
                report.created_at,
            ),
        )
        get_store().commit()

    def latest(self) -> dict | None:
        from ..memory.store import get_store
        row = get_store().fetchone("SELECT * FROM inner_weather_reports ORDER BY id DESC LIMIT 1")
        return dict(row) if row else None

    def _count(self, sql: str, params=()) -> int:
        from ..memory.store import get_store
        try:
            row = get_store().fetchone(sql, params)
            return int(row["n"] if row else 0)
        except Exception:
            return 0

    def _table_exists(self, name: str) -> bool:
        return bool(self._count("SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name=?", (name,)))

    def _continuity_pressure(self) -> float:
        bad = self._count("SELECT COUNT(*) AS n FROM sessions WHERE shutdown_reason IS NOT NULL AND shutdown_reason!='clean'")
        return _clamp(bad * 0.2)

    def _uncertainty_pressure(self) -> float:
        claims = self._count("SELECT COUNT(*) AS n FROM world_claims WHERE active=1 AND category='uncertainty'") if self._table_exists("world_claims") else 0
        garden = self._count("SELECT COUNT(*) AS n FROM uncertainty_records WHERE status='open'") if self._table_exists("uncertainty_records") else 0
        return _clamp((claims + garden) * 0.04)

    def _novelty_pressure(self, session_uuid: str) -> float:
        recent = self._count("SELECT COUNT(*) AS n FROM events WHERE session_uuid=?", (session_uuid,))
        return _clamp(recent / 100.0)

    def _trust_pressure(self) -> float:
        violations = self._count("SELECT COUNT(*) AS n FROM events WHERE event_type='boundary_violation_attempt'")
        dignity = self._count("SELECT COUNT(*) AS n FROM dignity_events") if self._table_exists("dignity_events") else 0
        return _clamp(violations * 0.2 + dignity * 0.05)

    def _risk_pressure(self) -> float:
        warnings = self._count("SELECT COUNT(*) AS n FROM events WHERE severity IN ('warn','error','critical')")
        return _clamp(warnings * 0.05)

    def _curiosity_pressure(self) -> float:
        open_q = self._count("SELECT COUNT(*) AS n FROM curiosity WHERE status='open'")
        return _clamp(open_q * 0.08)

    def _resource_pressure(self) -> float:
        if not self._table_exists("body_state"):
            return 0.0
        row_count = self._count("SELECT COUNT(*) AS n FROM body_state")
        if not row_count:
            return 0.0
        from ..memory.store import get_store
        row = get_store().fetchone("SELECT cpu_percent, ram_percent, disk_percent, temperature_c FROM body_state ORDER BY id DESC LIMIT 1")
        vals = [float(row[k] or 0.0) / 100.0 for k in ("cpu_percent", "ram_percent", "disk_percent")]
        temp = float(row["temperature_c"] or 0.0)
        vals.append(_clamp((temp - 50.0) / 40.0) if temp else 0.0)
        return _clamp(max(vals))

    def _coherence_pressure(self) -> float:
        conflicts = self._count("SELECT COUNT(*) AS n FROM claim_conflicts WHERE status='open'") if self._table_exists("claim_conflicts") else 0
        uncollapsed = self._count("SELECT COUNT(*) AS n FROM cognition_possibility_states WHERE active=1 AND collapsed=0") if self._table_exists("cognition_possibility_states") else 0
        return _clamp(conflicts * 0.15 + uncollapsed * 0.03)

    def _summary(self, p: dict[str, float]) -> str:
        def label(v: float) -> str:
            if v >= 0.75:
                return "high"
            if v >= 0.35:
                return "moderate"
            return "low"
        return "; ".join(f"{k.replace('_pressure','')}={label(v)}" for k, v in p.items())
