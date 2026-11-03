"""Fictional 4:4 motor-choice tests: eight poses, four choices, measured replay."""
import json
import math

import pytest

from bean.body.registry import BodyRegistry, init_registry_from_dict
from bean.body.state import BodyState
from bean.memory.audit_mirror import mirror_path
from bean.memory.event_logger import EventType, get_events_by_type
from bean.memory.store import init_store
from bean.motion.command import MotionCommand, CommandSource
from bean.motion.four_of_eight import (
    SCHEMA, FourOfEightSelector, ObservedOutcome, PoseCandidate,
)
from bean.motion.safety import MotionSafety
from bean.motion.simulator import MotionSimulator


JOINTS = ("finger_base", "finger_tip", "thumb_base", "thumb_tip")


def synthetic_body():
    return {"joints": [
        {"joint_id": jid, "label": "Synthetic " + jid, "neutral_pos": 20,
         "hardware_connected": False, "servo_channel": None,
         "limits": {"min_pos": 0, "max_pos": 90,
                    "safe_min": 10, "safe_max": 80, "max_speed": 30,
                    "forbidden_ranges": []}}
        for jid in JOINTS
    ], "limbs": [{"limb_id": "synthetic_hand", "label": "Synthetic hand",
                 "joint_ids": list(JOINTS)}]}


def poses():
    return tuple(
        PoseCandidate(
            candidate_id=f"pose-{i}",
            commands=tuple(MotionCommand.move_to(
                jid, 21.0 if i < 4 else 22.0, 10.0,
                source=CommandSource.TEST,
            ) for jid in JOINTS),
            signals=(1.0, 0.0) if i < 4 else (0.0, 1.0),
        ) for i in range(8)
    )


def plan(selector, options=None, cycle_id="synthetic-cycle-1"):
    return selector.plan(
        poses() if options is None else options,
        current_positions={j: 20.0 for j in JOINTS},
        max_delta_by_joint={j: 3.0 for j in JOINTS},
        cycle_id=cycle_id, step_ms=100,
    )


def test_eight_possibilities_become_four_coordinated_micro_positions():
    registry = init_registry_from_dict(synthetic_body())
    selector = FourOfEightSelector(MotionSafety(registry))
    result = plan(selector)
    preview = result.preview()
    assert preview["schema"] == SCHEMA
    assert preview["selected_positions"] == 4
    assert preview["candidates"] == 8
    assert preview["step_offsets_ms"] == [0, 100, 200, 300]
    assert [len(o.commands) for o in result.chosen] == [4, 4, 4, 4]
    assert preview["selected_ids"] == ["pose-0", "pose-1", "pose-2", "pose-3"]
    assert {v["reason"] for v in preview["withheld"]} == {"not_selected_unobserved"}
    assert preview["physical_feedback"] == "none"


def test_excluded_moves_are_not_mislabeled_and_unsafe_poses_cannot_be_selected():
    registry = init_registry_from_dict(synthetic_body())
    selector = FourOfEightSelector(MotionSafety(registry))
    all_options = list(poses())
    bad = all_options[0]
    all_options[0] = PoseCandidate(
        bad.candidate_id,
        (MotionCommand.move_to("finger_base", 999.0, 10.0, source=CommandSource.TEST),),
        bad.signals,
    )
    result = plan(selector, all_options)
    assert len(result.chosen) == 4
    assert result.chosen[0].candidate_id == "pose-1"
    assert dict(result.withheld)["pose-0"] == "joint_safety_rejected"
    assert all(x in dict(result.withheld) for x in ["pose-0", "pose-5", "pose-6", "pose-7"])
    with pytest.raises(ValueError, match="Fewer than four"):
        plan(selector, [
            PoseCandidate(p.candidate_id,
                          (MotionCommand.move_to("finger_base", 999., 10.),),
                          p.signals) if i < 5 else p
            for i, p in enumerate(poses())
        ])
    with pytest.raises(ValueError, match="Exactly eight"):
        plan(selector, poses()[:7])


def test_four_positions_simulate_only_and_revalidate_joints():
    registry = init_registry_from_dict(synthetic_body())
    safety = MotionSafety(registry)
    body = BodyState(registry=registry)
    simulation = MotionSimulator(body_state=body)
    result = plan(FourOfEightSelector(safety))
    assert len(result.chosen) == 4
    for pose in result.chosen:
        for command in pose.commands:
            verdict = safety.check(command, current_pos=body.get_joint(command.joint_id).position)
            assert verdict.approved
            assert simulation.execute(command, verdict).success
    assert all(body.get_joint(jid).position == 21.0 for jid in JOINTS)
    assert all(body.get_joint(jid).kind.value == "estimated" for jid in JOINTS)


def test_negative_evidence_revises_next_choice_after_sqlite_jsonl_restart(tmp_path):
    registry = BodyRegistry().load_from_dict(synthetic_body())
    db_path = tmp_path / "fictional_bean.sqlite"
    store = init_store(str(db_path))
    learner = FourOfEightSelector(MotionSafety(registry))
    first = plan(learner)
    assert tuple(o.candidate_id for o in first.chosen) == tuple(f"pose-{i}" for i in range(4))
    outcomes = [ObservedOutcome(
        candidate_id=o.candidate_id, reward=-1.0,
        evidence_ref=f"synthetic:test-{o.candidate_id}", provenance="synthetic",
    ) for o in first.chosen]
    event_id = learner.observe(first, outcomes, session_uuid="synthetic-session")
    assert event_id > 0
    next_plan = plan(learner, cycle_id="synthetic-cycle-2")
    assert tuple(o.candidate_id for o in next_plan.chosen) == tuple(f"pose-{i}" for i in range(4,8))
    rows = get_events_by_type(EventType.BODY_STATE, limit=100)
    assert len(rows) == 1
    payload = json.loads(rows[0]["data"])
    assert payload["schema"] == SCHEMA
    assert len(payload["observations"]) == 4
    assert all(row["provenance"] == "synthetic" for row in payload["observations"])
    mirror = mirror_path(db_path)
    assert mirror.exists()
    assert len(mirror.read_text().splitlines()) == 1
    assert '"receipt_sha256"' in mirror.read_text()
    store.close()
    init_store(str(db_path))
    replayed = FourOfEightSelector(MotionSafety(registry))
    assert replayed.replay(get_events_by_type(EventType.BODY_STATE, limit=100)) == 1
    assert replayed.weights == learner.weights
    assert plan(replayed, cycle_id="synthetic-cycle-3").preview()["selected_ids"] == [
        f"pose-{i}" for i in range(4,8)
    ]
    assert plan(FourOfEightSelector(MotionSafety(registry)),
                cycle_id="synthetic-baseline").preview()["selected_ids"] == [
        f"pose-{i}" for i in range(4)
    ]


def test_feedback_cannot_train_on_unchosen_options_or_unattributed_guesses(tmp_path):
    registry = BodyRegistry().load_from_dict(synthetic_body())
    init_store(str(tmp_path / "bean.sqlite"))
    learner = FourOfEightSelector(MotionSafety(registry))
    result = plan(learner)
    selected = [o.candidate_id for o in result.chosen]
    valid = [
        ObservedOutcome(s, -1., "synthetic:case-" + s, "synthetic")
        for s in selected
    ]
    with pytest.raises(ValueError, match="exactly"):
        learner.observe(result, valid[:3], session_uuid="synthetic-session")
    with pytest.raises(ValueError, match="exactly"):
        learner.observe(
            result, valid[:3] + [ObservedOutcome("pose-7", 1., "synthetic:other", "synthetic")],
            session_uuid="synthetic-session")
    with pytest.raises(ValueError, match="provenance"):
        learner.observe(
            result, valid[:3] + [ObservedOutcome(selected[3], -1., "synthetic:case", "inferred")],
            session_uuid="synthetic-session")
    with pytest.raises(ValueError, match="opaque"):
        learner.observe(
            result, valid[:3] + [ObservedOutcome(selected[3], -1., "private raw prompt", "synthetic")],
            session_uuid="synthetic-session")
    assert learner.weights == (1.0, 0.0)
    assert not get_events_by_type(EventType.BODY_STATE, limit=10)
