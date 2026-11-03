"""Review-only 4-of-8 micro-pose selector for BEAN's existing motion stack.

Eight distinct candidate poses, four predicted picks, then fresh observations.
A pose may coordinate several joints. The 4 selected poses are successive
positions, not simultaneous servo dispatch instructions. Nothing moves hardware.
Unselected candidates remain UNKNOWN, never automatically labelled "wrong".
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from .command import MotionCommand
from .safety import MotionSafety

SCHEMA = "bean.motion.four_of_eight.v1"
FEEDBACK_SUBTYPE = "four_of_eight_observation"
SAFE_REF = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")


@dataclass(frozen=True)
class PoseCandidate:
    candidate_id: str
    commands: tuple[MotionCommand, ...]
    signals: tuple[float, float]  # bounded, model-independent context features


@dataclass(frozen=True)
class ObservedOutcome:
    candidate_id: str
    reward: float  # externally evaluated goal progress, -1 to +1
    evidence_ref: str
    provenance: str  # synthetic, sensor, or human


@dataclass(frozen=True)
class FourOfEightPlan:
    cycle_id: str
    chosen: tuple[PoseCandidate, ...]
    withheld: tuple[tuple[str, str], ...]
    predicted: tuple[tuple[str, float], ...]
    step_ms: int

    def preview(self) -> dict:
        return {
            "schema": SCHEMA,
            "cycle_id": self.cycle_id,
            "status": "FOUR_MICRO_POSES_PLANNED_NOT_DISPATCHED",
            "candidates": 8,
            "selected_positions": len(self.chosen),
            "selected_ids": [p.candidate_id for p in self.chosen],
            "withheld": [{"candidate_id": cid, "reason": why} for cid, why in self.withheld],
            "predicted_utilities": [{"candidate_id": cid, "score": score} for cid, score in self.predicted],
            "step_offsets_ms": [i * self.step_ms for i in range(len(self.chosen))],
            "physical_feedback": "none",
        }


class FourOfEightSelector:
    """Two-weight online model; all learning comes from explicit feedback receipts."""

    def __init__(self, safety: MotionSafety, *, initial_weights=(1.0, 0.0),
                 learning_rate=1.0):
        self.safety = safety
        self.initial_weights = tuple(float(v) for v in initial_weights)
        if len(self.initial_weights) != 2 or not all(map(math.isfinite, self.initial_weights)):
            raise ValueError("Expected two finite initial weights")
        if not math.isfinite(learning_rate) or not 0 < learning_rate <= 1:
            raise ValueError("Learning rate must be in (0,1]")
        self.learning_rate = learning_rate
        self.weights = self.initial_weights

    def score(self, signals: tuple[float, float]) -> float:
        if len(signals) != 2 or not all(math.isfinite(v) and -1 <= v <= 1 for v in signals):
            raise ValueError("Expected two finite features in [-1,1]")
        return sum(w * x for w, x in zip(self.weights, signals))

    def plan(self, options: Sequence[PoseCandidate], *,
             current_positions: Mapping[str, float],
             max_delta_by_joint: Mapping[str, float],
             cycle_id: str, step_ms: int = 100) -> FourOfEightPlan:
        if len(options) != 8 or len({o.candidate_id for o in options}) != 8:
            raise ValueError("Exactly eight unique candidate poses required")
        if not cycle_id or not SAFE_REF.fullmatch(cycle_id):
            raise ValueError("A short safe cycle identifier is required")
        if type(step_ms) is not int or step_ms <= 0:
            raise ValueError("Positive integral micro-position interval required")
        for o in options:
            if not SAFE_REF.fullmatch(o.candidate_id) or not o.commands:
                raise ValueError("Each candidate needs an identifier and joint commands")
            if len({c.joint_id for c in o.commands}) != len(o.commands):
                raise ValueError("Each joint appears at most once per coordinated pose")
            self.score(o.signals)
        projected = dict(current_positions)
        ranked = sorted(enumerate(options), key=lambda ix: (-self.score(ix[1].signals), ix[0]))
        chosen: list[PoseCandidate] = []
        withheld: list[tuple[str, str]] = []
        for _, option in ranked:
            trial = dict(projected)
            reason = None
            for cmd in option.commands:
                position = trial.get(cmd.joint_id)
                limit = max_delta_by_joint.get(cmd.joint_id)
                if not isinstance(limit, (int, float)) or not math.isfinite(limit) or limit <= 0:
                    reason = "missing_joint_micro_step_limit"
                    break
                if position is None or not math.isfinite(position):
                    reason = "missing_observed_or_estimated_position"
                    break
                if not math.isfinite(cmd.target_pos) or not math.isfinite(cmd.speed):
                    reason = "nonfinite_motion"
                    break
                verdict = self.safety.check(cmd, current_pos=position)
                if not verdict.approved or verdict.resolved_target is None:
                    reason = "joint_safety_rejected"
                    break
                if abs(verdict.resolved_target - position) > limit + 1e-9:
                    reason = "micro_step_too_large"
                    break
                trial[cmd.joint_id] = verdict.resolved_target
            if reason:
                withheld.append((option.candidate_id, reason))
            elif len(chosen) < 4:
                chosen.append(option)
                projected = trial
            else:
                withheld.append((option.candidate_id, "not_selected_unobserved"))
        if len(chosen) != 4:
            raise ValueError("Fewer than four admissible poses: no partial plan")
        return FourOfEightPlan(
            cycle_id=cycle_id, chosen=tuple(chosen), withheld=tuple(withheld),
            predicted=tuple((o.candidate_id, self.score(o.signals)) for o in options),
            step_ms=step_ms,
        )

    def _apply_feedback(self, records: Sequence[dict]) -> None:
        for entry in records:
            signals = tuple(entry["signals"])
            reward = float(entry["reward"])
            error = reward - self.score(signals)
            denominator = 1 + sum(x*x for x in signals)
            self.weights = tuple(
                max(-4., min(4., w + self.learning_rate * error * x / denominator))
                for w, x in zip(self.weights, signals)
            )

    def observe(self, plan: FourOfEightPlan, outcomes: Sequence[ObservedOutcome], *,
                session_uuid: str) -> int:
        """Record observed outcomes in canonical SQLite/JSONL before revising model.

        Never learns from inferred success or from the four withheld candidates.
        A logging failure leaves this in-memory projection unchanged for replay.
        """
        ids = {p.candidate_id for p in plan.chosen}
        if len(outcomes) != 4 or {o.candidate_id for o in outcomes} != ids:
            raise ValueError("Feedback must identify exactly the four selected poses")
        if len({o.candidate_id for o in outcomes}) != 4:
            raise ValueError("Duplicate observation")
        if not session_uuid or not SAFE_REF.fullmatch(session_uuid):
            raise ValueError("Session identifier required for durable feedback")
        features = {p.candidate_id: p.signals for p in plan.chosen}
        rows = []
        for o in outcomes:
            if not math.isfinite(o.reward) or not -1 <= o.reward <= 1:
                raise ValueError("Observed reward must lie in [-1,1]")
            if o.provenance not in ("sensor", "human", "synthetic"):
                raise ValueError("Unsupported feedback provenance")
            if not SAFE_REF.fullmatch(o.evidence_ref):
                raise ValueError("Evidence must be an opaque reference, not raw data")
            rows.append({
                "candidate_id": o.candidate_id, "signals": list(features[o.candidate_id]),
                "reward": o.reward, "evidence_ref": o.evidence_ref,
                "provenance": o.provenance,
            })
        rows.sort(key=lambda r: [p.candidate_id for p in plan.chosen].index(r["candidate_id"]))
        payload = {"schema": SCHEMA, "cycle_id": plan.cycle_id, "observations": rows}
        payload["receipt_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        from ..memory.event_logger import EventType, Source, log_event
        source = (Source.SENSOR if all(o.provenance == "sensor" for o in outcomes)
                  else Source.HUMAN if all(o.provenance == "human" for o in outcomes)
                  else Source.SYSTEM)
        event_id = log_event(
            session_uuid, EventType.BODY_STATE,
            "4-of-8 review-only motion feedback recorded (four chosen, four unobserved).",
            source=source, subtype=FEEDBACK_SUBTYPE, data=payload,
        )
        self._apply_feedback(rows)
        return event_id

    def replay(self, events: Sequence[dict]) -> int:
        """Rebuild revisable weights from immutable Core event rows after restart."""
        ordered = sorted(events, key=lambda row: int(row["id"]))
        updates = []
        seen = set()
        for row in ordered:
            if row.get("event_type") != "body_state" or row.get("subtype") != FEEDBACK_SUBTYPE:
                continue
            data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
            if data.get("schema") != SCHEMA:
                continue
            digest = data.get("receipt_sha256")
            body = {k: v for k, v in data.items() if k != "receipt_sha256"}
            if hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest() != digest:
                raise ValueError("4-of-8 event checksum mismatch")
            if row["event_uuid"] in seen:
                raise ValueError("Duplicate event UUID")
            seen.add(row["event_uuid"])
            records = data["observations"]
            if len(records) != 4 or len({v["candidate_id"] for v in records}) != 4:
                raise ValueError("Invalid 4-of-8 observations")
            for v in records:
                if (v["provenance"] not in ("sensor", "human", "synthetic")
                    or not SAFE_REF.fullmatch(v["evidence_ref"])
                    or not -1 <= float(v["reward"]) <= 1):
                    raise ValueError("Invalid observation")
                self.score(tuple(v["signals"]))
            updates.append(records)
        self.weights = self.initial_weights
        for records in updates:
            self._apply_feedback(records)
        return len(updates)
