"""Private, evidence-oriented pre-match onboarding for the BEAN agent relay.

All records belong to one user's local agent. Never send this structure over
the inter-agent relay. The thresholds are research defaults, not validated
predictors of relationship success or psychological diagnostics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re

TOPICS = frozenset({
    "communication", "conflict", "lifestyle", "values", "attraction",
    "friendship", "ambitions", "boundaries", "daily_routines",
})
VIEWS = ("front", "left", "right")
CAPTURE = re.compile(r"^[0-9a-f]{64}$")
SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{4,64}$")
UTC = timezone.utc


def timestamp(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class EvaluationPolicy:
    minimum_days: int = 7
    minimum_sessions: int = 4
    minimum_distinct_days: int = 3
    minimum_topics: int = 5
    minimum_turns_per_session: int = 4
    minimum_seconds_per_session: int = 180
    mandatory_views: tuple[str, ...] = VIEWS


@dataclass
class LocalOnboarding:
    """Local-only readiness ledger with no raw dialogue or image contents."""

    started_at: datetime
    consent: bool = False
    sessions: dict = field(default_factory=dict)
    photos: dict = field(default_factory=dict)
    approved_by_human: bool = False
    policy: EvaluationPolicy = field(default_factory=EvaluationPolicy)

    def __post_init__(self):
        self.started_at = timestamp(self.started_at)

    def begin(self):
        self.consent = True

    def record_session(self, session_id, occurred_at, *, mode, topics,
                       turn_count, duration_seconds):
        if not self.consent:
            raise PermissionError("owner has not opted into evaluation")
        occurred_at = timestamp(occurred_at)
        if occurred_at < self.started_at:
            raise ValueError("session predates enrollment")
        if not isinstance(session_id, str) or not SESSION_ID.fullmatch(session_id):
            raise ValueError("invalid session id")
        if mode not in ("text", "voice"):
            raise ValueError("unknown conversation mode")
        if not isinstance(topics, (list, tuple, set)) or not topics:
            raise ValueError("topics required")
        values = sorted(set(topics))
        if any(not isinstance(x, str) or x not in TOPICS for x in values):
            raise ValueError("unrecognized topic")
        if type(turn_count) is not int or not 1 <= turn_count <= 10000:
            raise ValueError("invalid turn count")
        if type(duration_seconds) is not int or not 1 <= duration_seconds <= 86400:
            raise ValueError("invalid session duration")
        record = {"at": occurred_at.isoformat(), "mode": mode, "topics": values,
                  "turns": turn_count, "seconds": duration_seconds}
        previous = self.sessions.get(session_id)
        if previous and previous != record:
            raise ValueError("conflicting session receipt")
        self.sessions[session_id] = record
        return previous is None

    def record_photo(self, view, capture_sha256, clarity, *, owner_approved,
                     pose_verified=False):
        if not self.consent:
            raise PermissionError("owner has not opted into camera capture")
        if view not in self.policy.mandatory_views:
            raise ValueError("unsupported view")
        if not isinstance(capture_sha256, str) or not CAPTURE.fullmatch(capture_sha256):
            raise ValueError("invalid photo digest")
        if type(clarity) not in (int, float) or not 0 <= clarity <= 1:
            raise ValueError("invalid local sharpness/exposure score")
        if type(owner_approved) is not bool or type(pose_verified) is not bool:
            raise ValueError("explicit approval and pose provenance required")
        self.photos[view] = {
            "capture_digest": capture_sha256,
            "quality": float(clarity),
            "owner_approved": owner_approved,
            "pose_verified": pose_verified,
        }
        self.approved_by_human = False

    def status(self, now):
        now = timestamp(now)
        if now < self.started_at:
            raise ValueError("check time predates enrollment")
        eligible = [r for r in self.sessions.values()
                    if timestamp(r["at"]) <= now
                    and r["turns"] >= self.policy.minimum_turns_per_session
                    and r["seconds"] >= self.policy.minimum_seconds_per_session]
        dates = {timestamp(r["at"]).date() for r in eligible}
        topics = {t for r in eligible for t in r["topics"]}
        photos = {v for v in self.policy.mandatory_views
                  if (v in self.photos and self.photos[v]["owner_approved"]
                      and self.photos[v]["quality"] >= 0.60)}
        elapsed = (now - self.started_at).total_seconds()
        reasons = []
        if not self.consent:
            reasons.append("owner_consent_missing")
        if elapsed < self.policy.minimum_days * 86400:
            reasons.append("evaluation_period_incomplete")
        if len(eligible) < self.policy.minimum_sessions:
            reasons.append("insufficient_meaningful_sessions")
        if len(dates) < self.policy.minimum_distinct_days:
            reasons.append("insufficient_distinct_days")
        if len(topics) < self.policy.minimum_topics:
            reasons.append("insufficient_topic_coverage")
        if len(photos) < len(self.policy.mandatory_views):
            reasons.append("guided_photo_capture_incomplete")
        return {
            "schema": "bean.agent_relay.onboarding_status.v1",
            "evaluation_days": round(elapsed / 86400, 2),
            "meaningful_sessions": len(eligible),
            "distinct_days": len(dates),
            "explored_topics": len(topics),
            "approved_photo_views": sorted(photos),
            "voice_sessions": sum(r["mode"] == "voice" for r in eligible),
            "machine_pose_verified_views": sorted(
                v for v in photos if self.photos[v]["pose_verified"]),
            "eligible_for_human_review": not reasons,
            "human_approved": self.approved_by_human,
            "matching_enabled": not reasons and self.approved_by_human,
            "missing": reasons,
        }

    def confirm_ready(self, now):
        if not self.status(now)["eligible_for_human_review"]:
            raise ValueError("training is not complete")
        self.approved_by_human = True

    def public_gate(self, now):
        """Only a yes/no gate can leave local training. No private metrics."""
        return {"schema": "bean.agent_relay.readiness.v1",
                "matching_enabled": self.status(now)["matching_enabled"]}

    def local_receipt(self):
        """Metadata-only local export, never send to relay or public GitHub."""
        return {"schema": "bean.agent_relay.local_receipt.v1",
                "started_at": self.started_at.isoformat(), "consent": self.consent,
                "sessions": self.sessions, "photos": self.photos,
                "approved_by_human": self.approved_by_human}
