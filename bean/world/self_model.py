"""
bean/world/self_model.py

BEAN's structured beliefs about itself, derived from real records.
No introspection theater. No invented identity claims.
"""

from __future__ import annotations

import json
from typing import Optional

from .claim import Claim, ClaimCategory, ClaimSource, make_claim
from .model_store import ModelStore


class SelfModel:
    def __init__(self, store: Optional[ModelStore] = None):
        self._store = store or ModelStore()

    def update(self, session_uuid: str) -> list[Claim]:
        claims: list[Claim] = []
        claims.extend(self._derive_identity())
        claims.extend(self._derive_hardware())
        claims.extend(self._derive_history())
        claims.extend(self._derive_capabilities())
        claims.extend(self._derive_patterns())
        claims.extend(self._derive_uncertainties())
        self._store.save_many(claims)
        return claims

    def get(self, key: str) -> Optional[Claim]:
        return self._store.get_active(key)

    def get_value(self, key: str, default=None):
        claim = self.get(key)
        return claim.parsed_value(default) if claim else default

    def all_claims(self) -> list[Claim]:
        return [claim for claim in self._store.get_all_active() if claim.key.startswith("self.")]

    def snapshot(self) -> dict:
        claims = self.all_claims()
        return {
            "claim_count": len(claims),
            "claims": {
                claim.key: {
                    "content": claim.content,
                    "confidence": claim.confidence,
                    "source": claim.source_type.value,
                    "value": claim.parsed_value(),
                }
                for claim in sorted(claims, key=lambda c: c.key)
            },
        }

    def _derive_identity(self) -> list[Claim]:
        row = self._fetchone("SELECT * FROM identity WHERE id=1")
        if not row:
            return [
                make_claim(
                    "self.identity.unknown",
                    "I do not have an identity record in memory yet.",
                    ClaimCategory.UNCERTAINTY,
                    ClaimSource.EVENT_LOG,
                    1.0,
                )
            ]
        return [
            make_claim("self.identity.name", f"My recorded name is {row['name']}.", ClaimCategory.SELF, ClaimSource.BOOTSTRAP, 1.0, row["name"]),
            make_claim("self.identity.version", f"My recorded version is {row['version']}.", ClaimCategory.SELF, ClaimSource.BOOTSTRAP, 1.0, row["version"]),
            make_claim("self.identity.stage", f"My developmental stage is {row['developmental_stage']}.", ClaimCategory.SELF, ClaimSource.BOOTSTRAP, 1.0, row["developmental_stage"]),
            make_claim("self.identity.what_i_am", row["what_bean_is"], ClaimCategory.SELF, ClaimSource.BOOTSTRAP, 1.0, row["what_bean_is"]),
            make_claim("self.identity.what_i_am_not", row["what_bean_is_not"], ClaimCategory.SELF, ClaimSource.BOOTSTRAP, 1.0, row["what_bean_is_not"]),
        ]

    def _derive_hardware(self) -> list[Claim]:
        claims: list[Claim] = []
        row = self._fetchone("SELECT hardware_body FROM identity WHERE id=1")
        if row:
            try:
                body = json.loads(row["hardware_body"] or "{}")
            except Exception:
                body = {}
            if body.get("primary_brain"):
                claims.append(make_claim("self.hardware.primary_brain", f"My primary brain is {body['primary_brain']}.", ClaimCategory.SELF, ClaimSource.BOOTSTRAP, 1.0, body["primary_brain"]))
        try:
            from ..body.registry import get_registry
            registry = get_registry()
            total = len(registry.all_joints())
            connected = len(registry.connected_joints())
            claims.append(make_claim("self.hardware.total_joint_count", f"My body registry defines {total} joint(s).", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, total))
            claims.append(make_claim("self.hardware.connected_joint_count", f"{connected} of my {total} joint(s) have confirmed hardware connections.", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, connected))
            claims.append(make_claim("self.hardware.body_config_loaded", "A body registry config has been loaded and is active.", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, True))
        except Exception:
            claims.append(make_claim("self.hardware.body_config_loaded", "No body registry has been loaded in this session.", ClaimCategory.UNCERTAINTY, ClaimSource.EVENT_LOG, 1.0, False))
        return claims

    def _derive_history(self) -> list[Claim]:
        sessions = self._fetchone("SELECT COUNT(*) as n FROM sessions")["n"]
        events = self._fetchone("SELECT COUNT(*) as n FROM events")["n"]
        last = self._fetchone("SELECT shutdown_reason FROM sessions ORDER BY boot_count DESC LIMIT 1")
        unclean = self._fetchone("SELECT COUNT(*) as n FROM sessions WHERE shutdown_reason IS NOT NULL AND shutdown_reason NOT IN ('clean')")["n"]
        claims = [
            make_claim("self.history.total_sessions", f"I have {sessions} recorded session(s).", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, sessions),
            make_claim("self.history.total_boots", f"I have booted {sessions} time(s) in total.", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, sessions),
            make_claim("self.history.total_events", f"My event log contains {events} event(s).", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, events),
            make_claim("self.history.has_had_unclean_shutdown", f"I have had {unclean} unclean shutdown(s)." if unclean else "All recorded shutdowns have been clean.", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, bool(unclean)),
        ]
        if last and last["shutdown_reason"]:
            reason = last["shutdown_reason"]
            claims.append(make_claim("self.history.last_shutdown_reason", "My most recent session ended cleanly." if reason == "clean" else f"My most recent session ended with reason: {reason}.", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, reason))
        return claims

    def _derive_capabilities(self) -> list[Claim]:
        active = [r["name"] for r in self._fetchall("SELECT name FROM capabilities WHERE status='active' ORDER BY name")]
        planned = [r["name"] for r in self._fetchall("SELECT name FROM capabilities WHERE status='planned' ORDER BY name")]
        claims = [
            make_claim("self.capabilities.active", f"My active capabilities are: {', '.join(active)}." if active else "I have no active capabilities recorded.", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, active),
            make_claim("self.capabilities.planned", f"My planned capabilities are: {', '.join(planned)}." if planned else "No planned capabilities recorded.", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, planned),
        ]
        try:
            skills = self._fetchall("SELECT name, confidence, success_count FROM motion_skills ORDER BY name")
            confident = [r["name"] for r in skills if (r["confidence"] or 0) > 0]
            claims.append(make_claim("self.capabilities.skill_count", f"My skill library contains {len(skills)} defined skill(s).", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, len(skills)))
            claims.append(make_claim("self.capabilities.skills_with_confidence", f"I have earned confidence in {len(confident)} skill(s).", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, confident))
        except Exception:
            claims.append(make_claim("self.capabilities.skill_count", "No skill library found or initialized yet.", ClaimCategory.UNCERTAINTY, ClaimSource.EVENT_LOG, 1.0, 0))
        return claims

    def _derive_patterns(self) -> list[Claim]:
        avg = self._fetchone("SELECT AVG(n) as avg_events FROM (SELECT COUNT(*) as n FROM events GROUP BY session_uuid)")
        reflections = self._fetchone("SELECT COUNT(*) as n FROM reflections")["n"]
        open_q = self._fetchone("SELECT COUNT(*) as n FROM curiosity WHERE status='open'")["n"]
        errors = self._fetchone("SELECT COUNT(*) as n FROM events WHERE severity IN ('error','critical')")["n"]
        sessions = max(1, self._fetchone("SELECT COUNT(*) as n FROM sessions")["n"])
        claims = [
            make_claim("self.patterns.reflection_count", f"I have completed {reflections} reflection pass(es).", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, reflections),
            make_claim("self.patterns.open_question_count", f"I currently have {open_q} open curiosity question(s)." if open_q else "I have no open curiosity questions at this time.", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 1.0, open_q),
            make_claim("self.patterns.error_rate", f"I average {round(errors / sessions, 2)} error/critical event(s) per session.", ClaimCategory.SELF, ClaimSource.INFERENCE, 0.7, round(errors / sessions, 2)),
        ]
        if avg and avg["avg_events"] is not None:
            claims.append(make_claim("self.patterns.avg_session_event_count", f"On average, I generate {round(avg['avg_events'], 1)} event(s) per session.", ClaimCategory.SELF, ClaimSource.INFERENCE, 0.5 if sessions < 3 else 0.8, round(avg["avg_events"], 1)))
        return claims

    def _derive_uncertainties(self) -> list[Claim]:
        return [
            make_claim("self.uncertainty.no_sensor_feedback", "I cannot confirm actual joint positions. Joint positions are estimated from last commanded values only.", ClaimCategory.UNCERTAINTY, ClaimSource.BOOTSTRAP, 1.0),
            make_claim("self.uncertainty.no_hardware_motion", "I have not executed motion on real hardware yet. All motion so far has been simulated.", ClaimCategory.UNCERTAINTY, ClaimSource.BOOTSTRAP, 1.0),
        ]

    def _fetchone(self, sql: str, params=()):
        from ..memory.store import get_store
        return get_store().fetchone(sql, params)

    def _fetchall(self, sql: str, params=()):
        from ..memory.store import get_store
        return get_store().fetchall(sql, params)
