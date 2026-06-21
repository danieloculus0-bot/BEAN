"""Goal proposals derived from threatened drives. Proposals never self-execute."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .drive import DrivePriority, DriveState

GOAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS cognition_goal_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    goal_state TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_detail TEXT,
    motivation TEXT NOT NULL,
    drive_source TEXT,
    priority INTEGER NOT NULL,
    approval_required TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    supervisor_note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_proposals_session ON cognition_goal_proposals(session_uuid);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON cognition_goal_proposals(status);
"""


class ActionType(str, Enum):
    ASK_SUPERVISOR = "ask_supervisor"
    RUN_REFLECTION = "run_reflection"
    UPDATE_MODELS = "update_models"
    PRACTICE_SKILL = "practice_skill"
    REDUCE_LOAD = "reduce_load"
    NO_ACTION = "no_action"


class ApprovalRequired(str, Enum):
    NONE = "none"
    SUPERVISOR = "supervisor"
    HARDWARE = "hardware"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_goal_table():
    from ..memory.store import get_store
    get_store()._conn().executescript(GOAL_SCHEMA)
    get_store().commit()


@dataclass
class GoalProposal:
    goal_state: str
    action_type: ActionType
    motivation: str
    priority: int
    approval_required: ApprovalRequired
    action_detail: Optional[dict] = None
    drive_source: Optional[str] = None
    status: str = "pending"
    supervisor_note: Optional[str] = None
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)
    resolved_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {"proposal_id": self.proposal_id, "goal_state": self.goal_state, "action_type": self.action_type.value, "action_detail": self.action_detail, "motivation": self.motivation, "drive_source": self.drive_source, "priority": self.priority, "approval_required": self.approval_required.value, "status": self.status, "supervisor_note": self.supervisor_note, "created_at": self.created_at, "resolved_at": self.resolved_at}


class GoalStateEngine:
    def __init__(self):
        ensure_goal_table()

    def propose(self, session_uuid: str, threatened_drives: list[DriveState], open_questions: Optional[list[dict]] = None) -> list[GoalProposal]:
        proposals: list[GoalProposal] = []
        for drive in threatened_drives:
            proposal = self._drive_to_proposal(drive)
            if proposal:
                proposals.append(proposal)
        for q in open_questions or []:
            proposals.append(GoalProposal("answer_open_question", ActionType.ASK_SUPERVISOR, f"Open question may need supervisor evidence: {q.get('question')}", 4, ApprovalRequired.SUPERVISOR, {"question_id": q.get("id")}, "curiosity"))
        for proposal in proposals:
            self._persist(proposal, session_uuid)
        self._log_proposals(proposals, session_uuid)
        return proposals

    def approve(self, proposal_id: str, supervisor_note: str = "") -> bool:
        return self._resolve(proposal_id, "approved", supervisor_note)

    def reject(self, proposal_id: str, supervisor_note: str = "") -> bool:
        return self._resolve(proposal_id, "rejected", supervisor_note)

    def get_pending(self, session_uuid: str) -> list[GoalProposal]:
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT * FROM cognition_goal_proposals WHERE session_uuid=? AND status='pending' ORDER BY priority, id", (session_uuid,))
        return [self._row_to_proposal(r) for r in rows]

    def _drive_to_proposal(self, state: DriveState) -> Optional[GoalProposal]:
        mapping = {
            "avoid_unsafe_body_state": ("protect_body_state", ActionType.REDUCE_LOAD, ApprovalRequired.HARDWARE, "Reduce load or request supervisor check before hardware activity."),
            "reduce_uncertainty": ("reduce_uncertainty", ActionType.ASK_SUPERVISOR, ApprovalRequired.SUPERVISOR, "Ask for evidence that could resolve uncertainty."),
            "maintain_truthful_claims": ("refresh_models", ActionType.UPDATE_MODELS, ApprovalRequired.NONE, "Run model update to keep beliefs current."),
            "learn_approved_skills": ("practice_approved_skill", ActionType.PRACTICE_SKILL, ApprovalRequired.SUPERVISOR, "Request supervised practice for an approved skill."),
        }
        goal, action, approval, detail = mapping.get(state.name, (f"protect_{state.name}", ActionType.ASK_SUPERVISOR, ApprovalRequired.SUPERVISOR, "Ask supervisor before acting on this drive."))
        return GoalProposal(goal, action, detail, int(state.priority), approval, {"signals": state.signals}, state.name)

    def _persist(self, proposal: GoalProposal, session_uuid: str):
        from ..memory.store import get_store
        get_store().execute("""
            INSERT OR IGNORE INTO cognition_goal_proposals
                (proposal_id, session_uuid, goal_state, action_type, action_detail, motivation, drive_source, priority, approval_required, status, supervisor_note, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (proposal.proposal_id, session_uuid, proposal.goal_state, proposal.action_type.value, json.dumps(proposal.action_detail), proposal.motivation, proposal.drive_source, proposal.priority, proposal.approval_required.value, proposal.status, proposal.supervisor_note, proposal.created_at, proposal.resolved_at))
        get_store().commit()

    def _resolve(self, proposal_id: str, status: str, note: str) -> bool:
        from ..memory.store import get_store
        cur = get_store().execute("UPDATE cognition_goal_proposals SET status=?, supervisor_note=?, resolved_at=? WHERE proposal_id=?", (status, note, _now(), proposal_id))
        get_store().commit()
        return cur.rowcount > 0

    def _log_proposals(self, proposals: list[GoalProposal], session_uuid: str):
        if not proposals:
            return
        from ..memory.event_logger import log_event, EventType, Source
        log_event(session_uuid, EventType.SELF_MODEL_UPDATE, f"{len(proposals)} goal proposal(s) generated.", Source.SYSTEM, subtype="goal_proposals_generated", data={"proposals": [p.to_dict() for p in proposals]})

    def _row_to_proposal(self, row) -> GoalProposal:
        return GoalProposal(row["goal_state"], ActionType(row["action_type"]), row["motivation"], row["priority"], ApprovalRequired(row["approval_required"]), json.loads(row["action_detail"] or "null"), row["drive_source"], row["status"], row["supervisor_note"], row["proposal_id"], row["created_at"], row["resolved_at"])
