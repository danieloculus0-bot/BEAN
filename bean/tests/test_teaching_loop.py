"""
Tests for BEAN teaching, replay, confidence, and memory logging loop.
"""

import json
import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.body.registry import init_registry_from_dict
from bean.body.state import BodyState
from bean.motion.command import MotionCommand, CommandSource, MotionSequence
from bean.motion.safety import MotionSafety
from bean.motion.simulator import MotionSimulator
from bean.motion.skills import SkillLibrary, Skill, seed_initial_skills, _update_confidence
from bean.motion.teaching import TeachingLayer

CONFIG = Path(__file__).parent.parent / "config" / "body_registry.example.json"


def make_stack():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    tmpdir = tempfile.mkdtemp()
    init_store(str(Path(tmpdir) / "teaching_test.db"))
    bootstrap_identity()
    session_uuid = begin_session()
    registry = init_registry_from_dict(json.loads(CONFIG.read_text()))
    body_state = BodyState(registry=registry)
    safety = MotionSafety(registry=registry)
    simulator = MotionSimulator(body_state=body_state)
    library = SkillLibrary()
    teaching = TeachingLayer(safety=safety, simulator=simulator, library=library, body_state=body_state)
    return session_uuid, library, teaching


def safe_cmd():
    return MotionCommand.move_to("left_finger_curl", 10.0, 12.0, source=CommandSource.TEACHER)


def bad_cmd():
    return MotionCommand.move_to("left_finger_curl", 999.0, 999.0, source=CommandSource.TEACHER)


def test_confidence_bounds_and_asymmetry():
    assert _update_confidence(0.0, False) == 0.0
    assert _update_confidence(1.0, True) == 1.0
    assert _update_confidence(0.5, False) < 0.5
    assert (_update_confidence(0.5, True) - 0.5) < (0.5 - _update_confidence(0.5, False))


def test_teaching_creates_skill():
    session_uuid, library, teaching = make_stack()
    teaching.begin_teaching("test_open", taught_by="supervisor", session_uuid=session_uuid)
    assert teaching.teach_command(safe_cmd(), session_uuid=session_uuid).approved
    skill = teaching.commit_teaching(session_uuid=session_uuid)
    assert skill is not None
    assert library.exists("test_open")
    assert skill.confidence == 0.0


def test_teaching_with_only_rejected_commands_creates_no_skill():
    session_uuid, library, teaching = make_stack()
    teaching.begin_teaching("bad_skill", taught_by="supervisor", session_uuid=session_uuid)
    assert not teaching.teach_command(bad_cmd(), session_uuid=session_uuid).approved
    assert teaching.commit_teaching(session_uuid=session_uuid) is None
    assert not library.exists("bad_skill")


def test_replay_increases_confidence_and_logs_memory():
    session_uuid, library, teaching = make_stack()
    teaching.begin_teaching("open_hand", taught_by="supervisor", session_uuid=session_uuid)
    teaching.teach_command(safe_cmd(), session_uuid=session_uuid)
    teaching.commit_teaching(session_uuid=session_uuid)
    before = get_store().fetchone("SELECT COUNT(*) AS n FROM events WHERE session_uuid=?", (session_uuid,))["n"]
    result = teaching.replay_skill("open_hand", session_uuid=session_uuid)
    after = get_store().fetchone("SELECT COUNT(*) AS n FROM events WHERE session_uuid=?", (session_uuid,))["n"]
    assert result["success"]
    assert result["new_confidence"] > 0.0
    assert after > before


def test_stub_skill_fails_and_lowers_confidence():
    _, library, teaching = make_stack()
    stub = Skill(name="stub", description="stub", body_parts=[], sequence=MotionSequence(name="stub", commands=[]), confidence=0.5)
    library.save(stub)
    result = teaching.replay_skill("stub")
    assert not result["success"]
    assert library.load("stub").confidence < 0.5


def test_initial_skills_seed_and_stub_behavior():
    _, library, teaching = make_stack()
    result = seed_initial_skills(library)
    assert "open_left_hand" in result["seeded"]
    assert "look_toward_sound" in result["seeded"]
    assert teaching.replay_skill("open_left_hand")["success"]
    assert not teaching.replay_skill("look_toward_sound")["success"]
