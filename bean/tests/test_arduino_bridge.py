"""Synthetic Nano transport tests, not physical-arm acceptance tests."""
import json
from pathlib import Path

import pytest

from bean.body.registry import BodyRegistry
from bean.body.state import BodyState
from bean.motion.arduino_bridge import (
    ArduinoMotionBridge, MotionHardwareError, ServoCalibration, load_calibrations,
)
from bean.motion.command import MotionCommand, CommandIntent
from bean.motion.safety import MotionSafety

CONFIG = Path(__file__).resolve().parents[1] / "config" / "body_registry.example.json"


class FakeNano:
    def __init__(self, *, reply=b"ACK,1\n"):
        self.writes = []
        self.replies = [reply]

    def write(self, command):
        self.writes.append(command)

    def readline(self):
        return self.replies.pop(0) if self.replies else b""


def stack(reply=b"ACK,1\n", connected=True):
    config = json.loads(CONFIG.read_text())
    joint = next(j for j in config["joints"] if j["joint_id"] == "left_finger_curl")
    joint["hardware_connected"] = connected
    joint["servo_channel"] = 3
    registry = BodyRegistry().load_from_dict(config)
    state = BodyState(registry)
    nano = FakeNano(reply=reply)
    bridge = ArduinoMotionBridge(registry, MotionSafety(registry), nano, {
        "left_finger_curl": ServoCalibration(800, 2100),
    }, state)
    return bridge, nano, state


def test_dispatch_uses_existing_limits_and_pwm_mapping():
    bridge, nano, state = stack()
    out = bridge.send(MotionCommand.move_to("left_finger_curl", 30.0, 10.0))
    assert out.accepted_by_controller and not out.position_confirmed
    assert nano.writes == [b"M,1,3,1300\n"]
    assert state.get_joint("left_finger_curl").kind.value == "estimated"
    assert "no position sensor" in state.get_joint("left_finger_curl").notes


def test_reject_unsafe_motion_before_writing():
    bridge, nano, _ = stack()
    with pytest.raises(MotionHardwareError, match="MotionSafety rejected"):
        bridge.send(MotionCommand.move_to("left_finger_curl", 70, 10))
    assert nano.writes == []


def test_reject_unconnected_joint_before_writing():
    bridge, nano, _ = stack(connected=False)
    with pytest.raises(MotionHardwareError, match="no confirmed"):
        bridge.send(MotionCommand.move_to("left_finger_curl", 30, 10))
    assert nano.writes == []


def test_nano_error_does_not_update_position():
    bridge, _, state = stack(reply=b"ERR,1,RANGE\n")
    with pytest.raises(MotionHardwareError, match="ERR,1,RANGE"):
        bridge.send(MotionCommand.move_to("left_finger_curl", 20, 10))
    assert state.get_joint("left_finger_curl").position == 30.0


def test_no_ack_does_not_claim_completion():
    bridge, _, state = stack(reply=b"")
    with pytest.raises(MotionHardwareError, match="No matching Arduino ACK"):
        bridge.send(MotionCommand.move_to("left_finger_curl", 20, 10))
    assert state.get_joint("left_finger_curl").position == 30.0


def test_relative_requires_supplied_current_position():
    bridge, nano, _ = stack()
    cmd = MotionCommand("left_finger_curl", CommandIntent.MOVE_BY, 5, 10)
    with pytest.raises(MotionHardwareError, match="MotionSafety rejected"):
        bridge.send(cmd)
    assert nano.writes == []
    result = bridge.send(cmd, current_pos=20)
    assert result.requested_position == 25


def test_calibration_inverts_and_requires_explicit_limits(tmp_path):
    assert ServoCalibration(2200, 800).pulse_for(5, 5, 70) == 2200
    with pytest.raises(ValueError):
        ServoCalibration(2501, 1200)
    with pytest.raises(ValueError):
        ServoCalibration(1500, 1500)
    path = tmp_path / "calibration.json"
    path.write_text('{"left_finger_curl":{"pulse_at_min_us":800,"pulse_at_max_us":2100}}')
    assert load_calibrations(path)["left_finger_curl"].pulse_for(70, 5, 70) == 2100


def test_handshake():
    bridge, nano, _ = stack(reply=b"READY 1\n")
    bridge.handshake()
    assert nano.writes == [b"HELLO\n"]
