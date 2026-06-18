"""
Tests for BEAN motion safety and simulator path.
"""

import json
from pathlib import Path

from bean.body.registry import init_registry_from_dict
from bean.body.state import BodyState
from bean.motion.command import MotionCommand, CommandSource
from bean.motion.safety import MotionSafety
from bean.motion.simulator import MotionSimulator

CONFIG = Path(__file__).parent.parent / "config" / "body_registry.example.json"


def make_stack():
    registry = init_registry_from_dict(json.loads(CONFIG.read_text()))
    body_state = BodyState(registry=registry)
    safety = MotionSafety(registry=registry)
    simulator = MotionSimulator(body_state=body_state)
    return registry, body_state, safety, simulator


def test_safe_command_approved():
    _, _, safety, _ = make_stack()
    cmd = MotionCommand.move_to("left_finger_curl", 10.0, 12.0, source=CommandSource.TEST)
    verdict = safety.check(cmd, current_pos=30.0)
    assert verdict.approved


def test_unsafe_position_rejected():
    _, _, safety, _ = make_stack()
    cmd = MotionCommand.move_to("left_finger_curl", 999.0, 12.0, source=CommandSource.TEST)
    verdict = safety.check(cmd, current_pos=30.0)
    assert not verdict.approved
    assert verdict.violations


def test_unsafe_speed_rejected():
    _, _, safety, _ = make_stack()
    cmd = MotionCommand.move_to("left_finger_curl", 10.0, 999.0, source=CommandSource.TEST)
    verdict = safety.check(cmd, current_pos=30.0)
    assert not verdict.approved


def test_simulator_refuses_rejected_command():
    _, _, safety, simulator = make_stack()
    cmd = MotionCommand.move_to("left_finger_curl", 999.0, 12.0, source=CommandSource.TEST)
    verdict = safety.check(cmd, current_pos=30.0)
    result = simulator.execute(cmd, verdict)
    assert not result.success


def test_simulator_updates_body_state_for_safe_command():
    _, body_state, safety, simulator = make_stack()
    cmd = MotionCommand.move_to("left_finger_curl", 10.0, 12.0, source=CommandSource.TEST)
    verdict = safety.check(cmd, current_pos=30.0)
    result = simulator.execute(cmd, verdict)
    assert result.success
    assert body_state.get_joint("left_finger_curl").position == 10.0
