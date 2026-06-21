"""Lifecycle manager for possibility states."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from .possibility import PossibilityState, StateOption, build_initial_possibility_states, ensure_possibility_tables


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateCollapseManager:
    def __init__(self):
        ensure_possibility_tables()

    def seed_initial_states(self, overwrite: bool = False) -> dict:
        seeded, skipped = [], []
        for state in build_initial_possibility_states():
            if self._state_exists(state.name) and not overwrite:
                skipped.append(state.name)
                continue
            if overwrite:
                from ..memory.store import get_store
                get_store().execute("UPDATE cognition_possibility_states SET active=0 WHERE name=? AND active=1", (state.name,))
                get_store().commit()
            self._insert_state(state)
            seeded.append(state.name)
        return {"seeded": seeded, "skipped": skipped}

    def get(self, name: str) -> Optional[PossibilityState]:
        from ..memory.store import get_store
        row = get_store().fetchone("SELECT * FROM cognition_possibility_states WHERE name=? AND active=1 ORDER BY id DESC LIMIT 1", (name,))
        return self._row_to_state(row) if row else None

    def all_active(self) -> list[PossibilityState]:
        from ..memory.store import get_store
        return [self._row_to_state(r) for r in get_store().fetchall("SELECT * FROM cognition_possibility_states WHERE active=1 ORDER BY name")]

    def all_uncollapsed(self) -> list[PossibilityState]:
        return [s for s in self.all_active() if not s.collapsed]

    def update(self, state: PossibilityState):
        from ..memory.store import get_store
        state.updated_at = _now()
        get_store().execute("UPDATE cognition_possibility_states SET options=?, collapsed=?, collapsed_to=?, updated_at=? WHERE name=? AND active=1", (json.dumps([o.to_dict() for o in state.options]), 1 if state.collapsed else 0, state.collapsed_to, state.updated_at, state.name))
        get_store().commit()

    def record_reweight(self, state_name: str, observation: str, observation_ref: Optional[str], weights_before: dict[str, float], weights_after: dict[str, float], session_uuid: str):
        self._record_state_event(state_name, "reweight", observation, observation_ref, weights_before, weights_after, None, session_uuid)

    def collapse(self, state_name: str, option_key: str, observation: str, observation_ref: Optional[str], session_uuid: str) -> bool:
        state = self.get(state_name)
        if not state or not state.option(option_key):
            return False
        before = state.normalized_weights()
        state.collapsed = True
        state.collapsed_to = option_key
        for option in state.options:
            option.weight = 1.0 if option.key == option_key else 0.0
        self.update(state)
        after = state.normalized_weights()
        self._record_state_event(state_name, "collapse", observation, observation_ref, before, after, option_key, session_uuid)
        self._update_claim_after_collapse(state, option_key, observation, session_uuid)
        return True

    def supervisor_resolve(self, state_name: str, option_key: str, observation: str, session_uuid: str) -> bool:
        ok = self.collapse(state_name, option_key, observation, "supervisor", session_uuid)
        if ok:
            from ..memory.event_logger import log_event, EventType, Source
            log_event(session_uuid, EventType.SUPERVISOR_NOTE, f"Supervisor resolved possibility state {state_name} to {option_key}.", Source.HUMAN, subtype="possibility_state_supervisor_resolve", data={"state_name": state_name, "option_key": option_key, "observation": observation})
        return ok

    def reset_state(self, state_name: str, session_uuid: str, reason: str) -> bool:
        current = self.get(state_name)
        if not current:
            return False
        from ..memory.store import get_store
        get_store().execute("UPDATE cognition_possibility_states SET active=0 WHERE name=? AND active=1", (state_name,))
        fresh = next((s for s in build_initial_possibility_states() if s.name == state_name), None)
        if not fresh:
            return False
        self._insert_state(fresh)
        self._record_state_event(state_name, "reset", reason, "supervisor", current.normalized_weights(), fresh.normalized_weights(), None, session_uuid)
        return True

    def snapshot(self) -> list[dict]:
        return [s.to_dict() for s in self.all_active()]

    def history(self, state_name: str, limit: int = 20) -> list[dict]:
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT * FROM cognition_state_events WHERE state_name=? ORDER BY id DESC LIMIT ?", (state_name, limit))
        return [dict(r) for r in rows]

    def _state_exists(self, name: str) -> bool:
        from ..memory.store import get_store
        row = get_store().fetchone("SELECT COUNT(*) as n FROM cognition_possibility_states WHERE name=? AND active=1", (name,))
        return bool(row and row["n"])

    def _insert_state(self, state: PossibilityState):
        from ..memory.store import get_store
        get_store().execute("INSERT INTO cognition_possibility_states (state_id, name, description, options, collapsed, collapsed_to, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (state.state_id, state.name, state.description, json.dumps([o.to_dict() for o in state.options]), 1 if state.collapsed else 0, state.collapsed_to, 1 if state.active else 0, state.created_at, state.updated_at))
        get_store().commit()

    def _row_to_state(self, row) -> PossibilityState:
        return PossibilityState(row["state_id"], row["name"], row["description"], [StateOption.from_dict(d) for d in json.loads(row["options"] or "[]")], bool(row["collapsed"]), row["collapsed_to"], bool(row["active"]), row["created_at"], row["updated_at"])

    def _record_state_event(self, state_name, event_type, observation, observation_ref, before, after, collapsed_to, session_uuid):
        from ..memory.store import get_store
        get_store().execute("INSERT INTO cognition_state_events (event_id, state_name, event_type, observation, observation_ref, weights_before, weights_after, collapsed_to, session_uuid, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), state_name, event_type, observation, observation_ref, json.dumps(before), json.dumps(after), collapsed_to, session_uuid, _now()))
        get_store().commit()

    def _update_claim_after_collapse(self, state, option_key, observation, session_uuid):
        from ..world.claim import ClaimCategory, ClaimSource, make_claim
        from ..world.model_store import ModelStore
        ModelStore().save(make_claim(f"environment.possibility.{state.name}", f"Possibility state {state.name} collapsed to {option_key}: {observation}", ClaimCategory.ENVIRONMENT, ClaimSource.INFERENCE, 0.9, {"state": state.name, "collapsed_to": option_key, "observation": observation}))
