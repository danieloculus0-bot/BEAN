"""
bean/motion/skills.py

Named learned movements and skill confidence tracking.
Skills are persisted in SQLite through the BEAN memory store.
"""

from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..memory.store import get_store
from .command import MotionSequence, MotionCommand, CommandSource

CONFIDENCE_GAIN_PER_SUCCESS = 0.1
CONFIDENCE_LOSS_PER_FAILURE = 0.15


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_confidence(current: float, success: bool) -> float:
    delta = CONFIDENCE_GAIN_PER_SUCCESS if success else -CONFIDENCE_LOSS_PER_FAILURE
    return max(0.0, min(1.0, current + delta))


SKILLS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS motion_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_uuid TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    body_parts TEXT NOT NULL,
    sequence TEXT NOT NULL,
    preconditions TEXT,
    safety_notes TEXT,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    confidence REAL NOT NULL DEFAULT 0.0,
    last_practiced TEXT,
    taught_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def ensure_skills_table():
    store = get_store()
    store.execute(SKILLS_TABLE_SQL)
    store.commit()


@dataclass
class Skill:
    name: str
    description: str
    body_parts: list[str]
    sequence: MotionSequence
    preconditions: list[str] = field(default_factory=list)
    safety_notes: str = ""
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.0
    last_practiced: Optional[str] = None
    taught_by: str = "unknown"
    skill_uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def record_attempt(self, success: bool):
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.confidence = _update_confidence(self.confidence, success)
        self.last_practiced = _now()
        self.updated_at = _now()

    def reset_learning(self):
        self.success_count = 0
        self.failure_count = 0
        self.confidence = 0.0
        self.last_practiced = None
        self.updated_at = _now()

    def to_dict(self) -> dict:
        return {
            "skill_uuid": self.skill_uuid,
            "name": self.name,
            "description": self.description,
            "body_parts": self.body_parts,
            "sequence": self.sequence.to_dict(),
            "preconditions": self.preconditions,
            "safety_notes": self.safety_notes,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "confidence": self.confidence,
            "last_practiced": self.last_practiced,
            "taught_by": self.taught_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row) -> "Skill":
        d = dict(row)
        return cls(
            skill_uuid=d["skill_uuid"],
            name=d["name"],
            description=d["description"],
            body_parts=json.loads(d["body_parts"]),
            sequence=MotionSequence.from_dict(json.loads(d["sequence"])),
            preconditions=json.loads(d["preconditions"] or "[]"),
            safety_notes=d.get("safety_notes") or "",
            success_count=d.get("success_count") or 0,
            failure_count=d.get("failure_count") or 0,
            confidence=d.get("confidence") or 0.0,
            last_practiced=d.get("last_practiced"),
            taught_by=d.get("taught_by") or "unknown",
            created_at=d.get("created_at") or _now(),
            updated_at=d.get("updated_at") or _now(),
        )


class SkillLibrary:
    def __init__(self):
        ensure_skills_table()

    def save(self, skill: Skill):
        store = get_store()
        existing = store.fetchone("SELECT id FROM motion_skills WHERE name=?", (skill.name,))
        payload = (
            skill.skill_uuid,
            skill.name,
            skill.description,
            json.dumps(skill.body_parts),
            json.dumps(skill.sequence.to_dict()),
            json.dumps(skill.preconditions),
            skill.safety_notes,
            skill.success_count,
            skill.failure_count,
            skill.confidence,
            skill.last_practiced,
            skill.taught_by,
            skill.created_at,
            skill.updated_at,
        )
        if existing:
            store.execute(
                """
                UPDATE motion_skills SET skill_uuid=?, description=?, body_parts=?, sequence=?,
                preconditions=?, safety_notes=?, success_count=?, failure_count=?, confidence=?,
                last_practiced=?, taught_by=?, created_at=?, updated_at=? WHERE name=?
                """,
                (skill.skill_uuid, skill.description, json.dumps(skill.body_parts), json.dumps(skill.sequence.to_dict()),
                 json.dumps(skill.preconditions), skill.safety_notes, skill.success_count, skill.failure_count,
                 skill.confidence, skill.last_practiced, skill.taught_by, skill.created_at, skill.updated_at, skill.name),
            )
        else:
            store.execute(
                """
                INSERT INTO motion_skills (skill_uuid, name, description, body_parts, sequence,
                preconditions, safety_notes, success_count, failure_count, confidence, last_practiced,
                taught_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                payload,
            )
        store.commit()

    def load(self, name: str) -> Optional[Skill]:
        row = get_store().fetchone("SELECT * FROM motion_skills WHERE name=?", (name,))
        return Skill.from_row(row) if row else None

    def exists(self, name: str) -> bool:
        return self.load(name) is not None

    def all_names(self) -> list[str]:
        rows = get_store().fetchall("SELECT name FROM motion_skills ORDER BY name")
        return [r["name"] for r in rows]


def _seq(name: str, joint: str, pos: float, speed: float = 10.0) -> MotionSequence:
    return MotionSequence(
        name=name,
        commands=[MotionCommand.move_to(joint, pos, speed, source=CommandSource.SKILL_REPLAY, notes=f"Seeded skill: {name}")],
        source=CommandSource.SKILL_REPLAY,
    )


def seed_initial_skills(library: SkillLibrary) -> dict:
    specs = [
        ("open_left_hand", "Open left hand.", ["left_finger_curl"], _seq("open_left_hand", "left_finger_curl", 10.0, 12.0)),
        ("close_left_hand", "Close left hand.", ["left_finger_curl"], _seq("close_left_hand", "left_finger_curl", 55.0, 12.0)),
        ("raise_left_arm_small", "Raise left arm slightly.", ["left_shoulder_pitch"], _seq("raise_left_arm_small", "left_shoulder_pitch", 80.0, 10.0)),
        ("lower_left_arm_small", "Lower left arm slightly.", ["left_shoulder_pitch"], _seq("lower_left_arm_small", "left_shoulder_pitch", 100.0, 10.0)),
        ("look_toward_sound", "Future stub: orient toward sound.", [], MotionSequence(name="look_toward_sound", commands=[], source=CommandSource.SKILL_REPLAY)),
    ]
    seeded, skipped = [], []
    for name, desc, parts, sequence in specs:
        if library.exists(name):
            skipped.append(name)
            continue
        library.save(Skill(name=name, description=desc, body_parts=parts, sequence=sequence, safety_notes="Seeded safe starter skill or explicit future stub."))
        seeded.append(name)
    return {"seeded": seeded, "skipped": skipped}
