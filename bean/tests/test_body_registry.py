"""
Tests for BEAN Body Registry Core 0.1.
"""

import json
from pathlib import Path

from bean.body.registry import BodyRegistry, init_registry_from_dict
from bean.body.state import BodyState

CONFIG = Path(__file__).parent.parent / "config" / "body_registry.example.json"


def load_raw():
    return json.loads(CONFIG.read_text())


def test_registry_loads_example_config():
    registry = BodyRegistry().load_from_dict(load_raw())
    assert registry.joint_exists("left_finger_curl")
    assert registry.limb_exists("left_arm")
    assert len(registry.all_joints()) >= 5


def test_limb_references_known_joints():
    registry = BodyRegistry().load_from_dict(load_raw())
    joints = registry.joints_for_limb("left_hand")
    assert [j.joint_id for j in joints] == ["left_finger_curl"]


def test_body_state_initializes_to_neutral():
    registry = init_registry_from_dict(load_raw())
    state = BodyState(registry=registry)
    assert state.get_joint("left_finger_curl").position == 30.0
    assert state.is_at_neutral("left_finger_curl")


def test_connected_joints_default_empty():
    registry = BodyRegistry().load_from_dict(load_raw())
    assert registry.connected_joints() == []
