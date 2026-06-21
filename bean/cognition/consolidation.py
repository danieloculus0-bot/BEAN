"""Cognition consolidation pass: significance, surprise, preference, drive, goal, model update."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

CONSOLIDATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS cognition_consolidations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consolidation_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    trigger TEXT NOT NULL,
    events_reviewed INTEGER NOT NULL,
    significant_event_count INTEGER NOT NULL,
    surprises_found INTEGER NOT NULL,
    preferences_updated INTEGER NOT NULL,
    drives_evaluated INTEGER NOT NULL,
    proposals_generated INTEGER NOT NULL,
    questions_closed INTEGER NOT NULL,
    continuity_summary TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_consolidation_table():
    from ..memory.store import get_store
    get_store()._conn().executescript(CONSOLIDATION_SCHEMA)
    get_store().commit()


@dataclass
class ConsolidationReport:
    consolidation_id: str
    session_uuid: str
    trigger: str
    events_reviewed: int
    significant_event_count: int
    surprises_found: int
    preferences_updated: int
    drives_evaluated: int
    proposals_generated: int
    questions_closed: int
    continuity_summary: str
    created_at: str

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class ConsolidationEngine:
    def __init__(self, scorer=None, surprise_detector=None, preference_engine=None, drive_evaluator=None, goal_engine=None, model_updater=None):
        ensure_consolidation_table()
        self.scorer = scorer
        self.surprise = surprise_detector
        self.preference = preference_engine
        self.drive = drive_evaluator
        self.goal = goal_engine
        self.model_updater = model_updater

    def run(self, session_uuid: str, trigger: str = "manual", recent_events: Optional[list[dict]] = None) -> ConsolidationReport:
        from .significance import SignificanceScorer
        from .surprise import SurpriseDetector
        from .preference import PreferenceEngine
        from .drive import DriveEvaluator
        from .goal_state import GoalStateEngine
        from ..memory.event_logger import get_recent_events, log_event, EventType, Source
        events = recent_events if recent_events is not None else get_recent_events(session_uuid, 100)
        scorer = self.scorer or SignificanceScorer()
        significant = [s for s in scorer.score_events(events) if s.is_notable()]
        surprise = self.surprise or SurpriseDetector()
        surprises = surprise.check_events_batch(events, session_uuid)
        preference = self.preference or PreferenceEngine()
        prefs = preference.update_from_history(session_uuid)
        drive = self.drive or DriveEvaluator()
        drives = drive.evaluate_all(session_uuid)
        threatened = [d for d in drives if d.is_threatened()]
        questions = self._get_open_questions()
        goal = self.goal or GoalStateEngine()
        proposals = goal.propose(session_uuid, threatened, questions)
        if self.model_updater:
            self.model_updater.run(session_uuid, trigger=f"consolidation:{trigger}")
        closed = self._close_resolved_questions(session_uuid)
        summary = self._write_continuity_summary(session_uuid, len(events), len(significant), len(surprises), len(prefs), len(threatened), len(proposals), closed)
        report = ConsolidationReport(str(uuid.uuid4()), session_uuid, trigger, len(events), len(significant), len(surprises), len(prefs), len(drives), len(proposals), closed, summary, _now())
        self._persist(report)
        log_event(session_uuid, EventType.MEMORY_CONSOLIDATION, "Cognition consolidation pass complete.", Source.SYSTEM, subtype=f"consolidation:{trigger}", data=report.to_dict())
        return report

    def _get_open_questions(self) -> list[dict]:
        from ..memory.store import get_store
        return [dict(r) for r in get_store().fetchall("SELECT * FROM curiosity WHERE status='open' ORDER BY id DESC LIMIT 10")]

    def _close_resolved_questions(self, session_uuid: str) -> int:
        from ..memory.store import get_store
        facts = get_store().fetchall("SELECT summary FROM events WHERE session_uuid=? AND event_type='fact_learned' ORDER BY id DESC LIMIT 25", (session_uuid,))
        if not facts:
            return 0
        questions = get_store().fetchall("SELECT id, question FROM curiosity WHERE status='open'")
        closed = 0
        fact_text = "\n".join(r["summary"].lower() for r in facts)
        for q in questions:
            qt = q["question"].lower()
            if any(word in fact_text for word in qt.replace("?", "").split() if len(word) > 5):
                get_store().execute("UPDATE curiosity SET status='answered', answer=?, answered_at=? WHERE id=?", ("Resolved by logged fact during consolidation.", _now(), q["id"]))
                closed += 1
        get_store().commit()
        return closed

    def _write_continuity_summary(self, session_uuid: str, events, significant, surprises, prefs, threatened, proposals, closed) -> str:
        summary = f"Cognition consolidation reviewed {events} event(s). {significant} were significant, {surprises} surprise(s) were found, {prefs} preference update(s) were made, {threatened} drive(s) were threatened, {proposals} goal proposal(s) were produced, and {closed} question(s) were closed."
        from ..memory.store import get_store
        get_store().execute("INSERT INTO continuity_summaries (session_uuid, summary_type, content) VALUES (?, 'consolidation', ?)", (session_uuid, summary))
        get_store().commit()
        return summary

    def _persist(self, report: ConsolidationReport):
        from ..memory.store import get_store
        get_store().execute("INSERT INTO cognition_consolidations (consolidation_id, session_uuid, trigger, events_reviewed, significant_event_count, surprises_found, preferences_updated, drives_evaluated, proposals_generated, questions_closed, continuity_summary, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (report.consolidation_id, report.session_uuid, report.trigger, report.events_reviewed, report.significant_event_count, report.surprises_found, report.preferences_updated, report.drives_evaluated, report.proposals_generated, report.questions_closed, report.continuity_summary, report.created_at))
        get_store().commit()
