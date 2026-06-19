"""
bean/world/updater.py

Bridge from raw memory events to structured self/world beliefs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .claim import ClaimCategory
from .model_store import ModelStore
from .self_model import SelfModel
from .world_model import WorldModel


class ModelUpdater:
    def __init__(self, self_model: Optional[SelfModel] = None, world_model: Optional[WorldModel] = None, store: Optional[ModelStore] = None):
        self._store = store or ModelStore()
        self._self_model = self_model or SelfModel(store=self._store)
        self._world_model = world_model or WorldModel(store=self._store)
        self._last_update_at: Optional[str] = None
        self._update_count = 0

    def run(self, session_uuid: str, trigger: str = "tick") -> dict:
        from ..memory.event_logger import log_event, EventType, Source
        before = self._store.count_active()
        self_claims = self._self_model.update(session_uuid)
        world_claims = self._world_model.update(session_uuid)
        after = self._store.count_active()
        self._last_update_at = datetime.now(timezone.utc).isoformat()
        self._update_count += 1
        summary = {
            "trigger": trigger,
            "update_count": self._update_count,
            "self_claims_derived": len(self_claims),
            "world_claims_derived": len(world_claims),
            "total_active_claims": after,
            "net_active_claim_delta": after - before,
            "updated_at": self._last_update_at,
        }
        log_event(
            session_uuid=session_uuid,
            event_type=EventType.WORLD_MODEL_UPDATE,
            subtype=f"model_update:{trigger}",
            summary=f"Models updated ({trigger}): {len(self_claims)} self claims, {len(world_claims)} world claims.",
            source=Source.SYSTEM,
            data=summary,
        )
        return summary

    def run_self_only(self, session_uuid: str) -> dict:
        claims = self._self_model.update(session_uuid)
        self._last_update_at = datetime.now(timezone.utc).isoformat()
        return {"self_claims_derived": len(claims), "updated_at": self._last_update_at}

    def run_world_only(self, session_uuid: str) -> dict:
        claims = self._world_model.update(session_uuid)
        self._last_update_at = datetime.now(timezone.utc).isoformat()
        return {"world_claims_derived": len(claims), "updated_at": self._last_update_at}

    @property
    def self_model(self) -> SelfModel:
        return self._self_model

    @property
    def world_model(self) -> WorldModel:
        return self._world_model

    @property
    def store(self) -> ModelStore:
        return self._store

    def full_snapshot(self) -> dict:
        return {
            "updated_at": self._last_update_at,
            "update_count": self._update_count,
            "self_model": self._self_model.snapshot(),
            "world_model": self._world_model.snapshot(),
            "uncertainties": [claim.to_dict() for claim in self._store.get_uncertainties()],
        }
