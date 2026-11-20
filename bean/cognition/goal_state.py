"""Goal proposals derived from threatened drives. Proposals never self-execute."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, replace
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
    RUN_EXPERIMENT = "run_experiment"


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


PLAN_SCHEMA = "bean.goal.plan.v1"


def plan_proposal_id(plan_id: str, step: int) -> str:
    if (not isinstance(plan_id, str) or not 1 <= len(plan_id) <= 100
            or not plan_id.isascii()
            or any(not (c.isalnum() or c in "._:-") for c in plan_id)):
        raise ValueError("plan_id must be a bounded ASCII identifier")
    if type(step) is not int or not 0 <= step < 16:
        raise ValueError("plan step must be 0..15")
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{PLAN_SCHEMA}:{plan_id}:{step}"))


def goal_plan(detail: Optional[dict], proposal_id: str) -> Optional[dict]:
    """Validate reserved plan metadata without interpreting arbitrary inputs."""
    if not isinstance(detail, dict) or "goal_plan" not in detail:
        return None
    plan = detail["goal_plan"]
    if (not isinstance(plan, dict)
            or set(plan) != {"schema", "id", "step", "steps"}
            or plan.get("schema") != PLAN_SCHEMA
            or type(plan.get("steps")) is not int
            or not 1 <= plan["steps"] <= 16
            or type(plan.get("step")) is not int
            or not 0 <= plan["step"] < plan["steps"]
            or plan_proposal_id(plan.get("id"), plan["step"]) != proposal_id):
        raise ValueError("invalid persisted goal plan")
    return plan


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

    def propose_plan(self, session_uuid: str, plan_id: str,
                     steps: list[GoalProposal]) -> list[GoalProposal]:
        """Atomically persist a host-authored ordered plan in existing goals.

        A stable plan ID resumes the same immutable step identities across
        sessions. Revising a plan requires a new ID; it never resets attempts.
        This creates no capabilities or approvals and invents no model plan.
        """
        plan_proposal_id(plan_id, 0)
        if (not isinstance(steps, list) or not 1 <= len(steps) <= 16
                or any(not isinstance(s, GoalProposal) or s.status != "pending"
                       or not isinstance(s.action_detail, (dict, type(None)))
                       or (s.action_detail and "goal_plan" in s.action_detail)
                       for s in steps)):
            raise ValueError("plan requires 1..16 pending GoalProposal templates")
        planned = [replace(s, proposal_id=plan_proposal_id(plan_id, i),
                           action_detail={**(s.action_detail or {}), "goal_plan": {
                               "schema": PLAN_SCHEMA, "id": plan_id,
                               "step": i, "steps": len(steps)}})
                   for i, s in enumerate(steps)]
        # Freeze the caller's objects to the exact JSON representation that
        # will be persisted (including tuple/list normalization).
        planned = [replace(p, action_detail=json.loads(json.dumps(
            p.action_detail, allow_nan=False, sort_keys=True))) for p in planned]
        from ..memory.store import get_store
        conn = get_store()._conn()
        fresh = []
        conn.execute("BEGIN IMMEDIATE")
        try:
            present = sum(conn.execute(
                "SELECT 1 FROM cognition_goal_proposals WHERE proposal_id=?",
                (p.proposal_id,)).fetchone() is not None for p in planned)
            if present not in (0, len(planned)):
                raise ValueError("incomplete persisted plan; inspect original evidence")
            fields = ("goal_state", "action_type", "motivation", "drive_source",
                      "priority", "approval_required")
            for proposal in planned:
                old = conn.execute(
                    "SELECT * FROM cognition_goal_proposals WHERE proposal_id=?",
                    (proposal.proposal_id,)).fetchone()
                if old is not None:
                    desired = proposal.to_dict()
                    if (any(old[k] != desired[k] for k in fields)
                            or json.loads(old["action_detail"]) != proposal.action_detail):
                        raise ValueError("existing plan is immutable; use a new plan_id")
                else:
                    self._persist(proposal, session_uuid, commit=False, strict=True)
                    fresh.append(proposal)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        self._log_proposals(fresh, session_uuid)
        return [self._row_to_proposal(conn.execute(
            "SELECT * FROM cognition_goal_proposals WHERE proposal_id=?",
            (p.proposal_id,)).fetchone()) for p in planned]

    def propose(self, session_uuid: str, threatened_drives: list[DriveState], open_questions: Optional[list[dict]] = None) -> list[GoalProposal]:
        proposals: list[GoalProposal] = []
        for drive in threatened_drives:
            proposal = self._drive_to_proposal(drive)
            if proposal:
                proposals.append(proposal)
        for q in open_questions or []:
            context = q.get("context")
            try:
                candidate = json.loads(context) if isinstance(context, str) else context
            except (TypeError, ValueError):
                candidate = None
            if (isinstance(candidate, dict)
                    and candidate.get("schema") == "bean.cognition.skill_question.v1"
                    and isinstance(candidate.get("skill_id"), str)
                    and 2 <= len(candidate["skill_id"]) <= 64
                    and candidate["skill_id"][0].islower()
                    and candidate["skill_id"][0].isascii()
                    and all(ch.isascii() and
                            (ch.islower() or ch.isdigit() or ch in "_:-")
                            for ch in candidate["skill_id"])):
                # Curiosity selects a skill ID from a host-owned, independently
                # evaluated curriculum. It cannot choose executable paths,
                # provider credentials, test labels or source code.
                skill_id = candidate["skill_id"]
                proposals.append(GoalProposal(
                    "investigate_open_question", ActionType.RUN_EXPERIMENT,
                    "Learn a reusable skill motivated by open curiosity", 3,
                    ApprovalRequired.NONE,
                    {"capability": "native_skill_incubator",
                     "skill_id": skill_id,
                     "learning_context": "skill:" + skill_id},
                    "curiosity"))
            elif (isinstance(candidate, dict)
                    and candidate.get("schema") == "bean.cognition.experiment.v1"
                    and isinstance(candidate.get("capability"), str)
                    and isinstance(candidate.get("inputs"), dict)
                    and isinstance(candidate.get("expected_output"), dict)):
                # A structured problem becomes a native investigation goal;
                # a separate authorized host still owns experimental actions.
                proposals.append(GoalProposal(
                    "investigate_open_question", ActionType.RUN_EXPERIMENT,
                    f"Find a tested method for: {q.get('question')}", 3,
                    ApprovalRequired.NONE,
                    {"question_id": q.get("id"), "capability": candidate["capability"],
                     "inputs": candidate["inputs"],
                     "expected_output": candidate["expected_output"]}, "curiosity"))
            else:
                proposals.append(GoalProposal(
                    "answer_open_question", ActionType.ASK_SUPERVISOR,
                    f"Open question may need supervisor evidence: {q.get('question')}",
                    4, ApprovalRequired.SUPERVISOR, {"question_id": q.get("id")},
                    "curiosity"))

        # Open questions outlive sessions and attempts. Re-proposing an
        # unchanged experiment would bypass GoalCycle's no-replay history,
        # including after failure or an interrupted action with unknown effects.
        # Preserve the original proposal in every state; changed inputs or
        # predictions form a new signature and may be investigated again.
        # Ordinary drive goals retain their existing session-local semantics.
        from ..memory.store import get_store
        pending = get_store().fetchall(
            "SELECT goal_state, action_type, action_detail, drive_source "
            "FROM cognition_goal_proposals "
            "WHERE (session_uuid=? AND status='pending') OR "
            "(goal_state='investigate_open_question' "
            "AND action_type='run_experiment' AND drive_source='curiosity')",
            (session_uuid,))
        existing = {
            (row["goal_state"], row["action_type"],
             json.dumps(json.loads(row["action_detail"] or "null"),
                        sort_keys=True), row["drive_source"])
            for row in pending}
        fresh = []
        for proposal in proposals:
            signature = (proposal.goal_state, proposal.action_type.value,
                         json.dumps(proposal.action_detail, sort_keys=True),
                         proposal.drive_source)
            if signature in existing:
                continue
            existing.add(signature)
            self._persist(proposal, session_uuid)
            fresh.append(proposal)
        self._log_proposals(fresh, session_uuid)
        return fresh

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

    def _persist(self, proposal: GoalProposal, session_uuid: str, *, commit=True, strict=False):
        from ..memory.store import get_store
        # A plan transaction must surface constraint failures so all prior
        # inserts roll back. Ordinary proposals retain legacy deduplication.
        prefix = "INSERT INTO" if strict else "INSERT OR IGNORE INTO"
        get_store().execute(prefix + """ cognition_goal_proposals
                (proposal_id, session_uuid, goal_state, action_type, action_detail, motivation, drive_source, priority, approval_required, status, supervisor_note, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (proposal.proposal_id, session_uuid, proposal.goal_state, proposal.action_type.value, json.dumps(proposal.action_detail), proposal.motivation, proposal.drive_source, proposal.priority, proposal.approval_required.value, proposal.status, proposal.supervisor_note, proposal.created_at, proposal.resolved_at))
        if commit:
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
