"""Native BEAN goal-to-skill learning, controlled synthetic integration tests."""
import json
from pathlib import Path

import pytest

from bean.cognition.goal_state import ActionType, GoalStateEngine
from bean.memory.store import _local, get_store, init_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.runtime.goal_cycle import GoalCycle
from bean.runtime.native_skill_experiment import (
    load_skill_catalog, make_native_skill_experiment,
    propose_skill_from_curiosity)


GOOD = "def double(value):\n    return value * 2\n"
OVERFIT = "def double(value):\n    return value * 2 if 0 <= value <= 3 else 0\n"


class Model:
    def __init__(self, code=GOOD):
        self.code = code
        self.calls = []

    def complete(self, prompt, context):
        self.calls.append((prompt, context))
        return {
            "ok": True, "raw_text": self.code,
            "model_name": "synthetic-writer",
            "adapter_name": "synthetic_fixture",
            "provider_response_id": "fixture-only"}


class Core:
    def __init__(self, model):
        self.model = model


def make_project(root, cases):
    (root / "tests").mkdir(parents=True)
    (root / "bean" / "skills").mkdir(parents=True)
    (root / "bean" / "__init__.py").write_text("")
    (root / "bean" / "skills" / "__init__.py").write_text("")
    body = "\n".join(
        f"    def test_case_{index}(self):\n"
        f"        self.assertEqual(double({value}), {answer})"
        for index, (value, answer) in enumerate(cases))
    (root / "tests" / "test_double.py").write_text(
        "import unittest\n"
        "from bean.skills.double import double\n"
        "class DoubleChecks(unittest.TestCase):\n" + body + "\n")
    return root


@pytest.fixture
def world(tmp_path):
    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    init_store(str(tmp_path / "bean_core.sqlite"))
    bootstrap_identity()
    session = begin_session()
    make_project(tmp_path / "training", [(2, 4), (3, 6)])
    make_project(tmp_path / "holdout", [(7, 14), (-3, -6)])
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({
        "schema": "bean.native_skill_catalog.v1",
        "skills": [{
            "skill_id": "double", "name": "double",
            "objective": "Implement a reusable doubling function for signed integers",
            "training_project": "training", "holdout_project": "holdout"}]}))
    yield tmp_path, session, path
    get_store().close()
    _local.conn = None


def handler(tmp_path, path, model, fallback=None):
    return make_native_skill_experiment(
        Core(model), catalog=load_skill_catalog(path),
        journal_path=tmp_path / "skill_journal.sqlite",
        output=tmp_path / "skill_artifacts",
        attempts=2, fallback=fallback)


def question(skill_id="double"):
    return {
        "id": 17, "question": "Can BEAN develop a reusable doubling skill?",
        "context": {"schema": "bean.cognition.skill_question.v1",
                    "skill_id": skill_id}}


def test_curiosity_proposes_executes_and_persists_real_skill_without_replay(world):
    root, session, path = world
    proposal = GoalStateEngine().propose(session, [], [question()])[0]
    assert proposal.action_type == ActionType.RUN_EXPERIMENT
    assert proposal.action_detail["capability"] == "native_skill_incubator"
    model = Model()
    cycle = GoalCycle({"run_experiment": handler(root, path, model)})
    receipt = cycle.poll_due()[0]
    assert receipt["status"] == "success"
    observed = json.loads(cycle.history()[0]["result_json"])
    assert observed["skill_promotion_ready"] is True
    assert observed["created_executable_code"] is True
    assert observed["author_model"] == "synthetic-writer"
    assert observed["independent_outcome_verified"] is False
    assert observed["model_weights_trained"] is False
    assert observed["installed_into_core"] is False
    assert len(model.calls) == 1
    assert "7, 14" not in model.calls[0][0]
    assert "(-3, -6)" not in model.calls[0][0]
    assert (root / "skill_artifacts/validated/bean/skills/double.py").read_text() == GOOD
    restarted = GoalCycle({"run_experiment": handler(root, path, Model())})
    assert restarted.recover_interrupted() == 0
    assert restarted.poll_due() == []
    assert GoalStateEngine().propose(begin_session(), [], [question()]) == []
    assert len(restarted.history()) == 1


def test_unseen_skill_id_is_never_executed(world):
    root, session, path = world
    model = Model()
    action = handler(root, path, model)
    assert action({"action_detail": {
        "capability": "native_skill_incubator",
        "skill_id": "not_in_catalog"}})["reason"] == "skill_not_in_host_catalog"
    assert model.calls == []
    assert not (root / "skill_journal.sqlite").exists()
    result = action({"action_detail": {
        "capability": "native_skill_incubator", "skill_id": "double",
        "training_project": "/tmp/forged"}})
    assert result["reason"] == "untrusted_skill_arguments"
    assert model.calls == []


def test_negative_holdout_stops_skill_creation_and_goals_do_not_repeat(world):
    root, session, path = world
    GoalStateEngine().propose(session, [], [question()])
    model = Model(OVERFIT)
    cycle = GoalCycle({"run_experiment": handler(root, path, model)})
    receipt = cycle.poll_due()[0]
    assert receipt["status"] == "n/a"
    observed = json.loads(cycle.history()[0]["result_json"])
    assert observed["incubation_status"] == "holdout_rejected"
    assert observed["skill_promotion_ready"] is False
    assert observed["created_executable_code"] is False
    assert len(model.calls) == 1
    assert cycle.poll_due() == []
    assert not (root / "skill_artifacts/validated/bean/skills/double.py").exists()


def test_native_reasoning_experiments_still_route_to_original_handler(world):
    root, _, path = world
    calls = []
    def fallback(goal):
        calls.append(goal)
        return {"status": "unverified", "reason": "original_native_experiment"}
    action = handler(root, path, Model(), fallback=fallback)
    req = {"action_detail": {
        "capability": "native_reason_local", "inputs": {"query": "x"}}}
    assert action(req)["reason"] == "original_native_experiment"
    assert calls == [req]


def test_bad_skill_question_is_not_executable(world):
    _, session, _ = world
    request = question("../inject")
    rows = GoalStateEngine().propose(session, [], [request])
    assert len(rows) == 1
    assert rows[0].action_type == ActionType.ASK_SUPERVISOR


def test_missing_model_abstains_without_skill_writes(world):
    root, _, path = world
    action = handler(root, path, None)
    result = action({"action_detail": {
        "capability": "native_skill_incubator", "skill_id": "double"}})
    assert result["status"] == "unverified"
    assert result["reason"] == "no_live_core_model"
    assert not (root / "skill_journal.sqlite").exists()


def test_catalog_rejects_ambiguous_or_repeated_skills(world):
    root, _, path = world
    catalog = json.loads(path.read_text())
    catalog["skills"].append(catalog["skills"][0])
    path.write_text(json.dumps(catalog))
    with pytest.raises(ValueError, match="duplicate"):
        load_skill_catalog(path)
    catalog["skills"][1]["skill_id"] = "also_double"
    catalog["skills"][1]["holdout_project"] = "training"
    path.write_text(json.dumps(catalog))
    with pytest.raises(ValueError, match="separate"):
        load_skill_catalog(path)


class ModelThatSelectsAndWrites:
    def __init__(self, question_id, skill_id="double"):
        self.question_id = question_id
        self.skill_id = skill_id
        self.calls = []

    def complete(self, prompt, context):
        self.calls.append((prompt, context))
        if "Unresolved questions:" in prompt:
            result = json.dumps({"skill_id": self.skill_id,
                                 "question_id": self.question_id})
        else:
            result = GOOD
        return {"ok": True, "raw_text": result,
                "model_name": "synthetic-dual-model",
                "adapter_name": "synthetic_fixture"}


def insert_curiosity(question):
    get_store().execute(
        "INSERT INTO curiosity (question,context,status) VALUES (?,?,?)",
        (question, "synthetic independent observation", "open"))
    get_store().commit()
    return get_store().fetchone(
        "SELECT id FROM curiosity WHERE question=?", (question,))["id"]


def test_bean_autonomously_selects_new_skill_from_own_curiosity_and_executes(world):
    root, session, path = world
    question_id = insert_curiosity(
        "How could a reusable doubling skill explain this repeated numeric pattern?")
    model = ModelThatSelectsAndWrites(question_id)
    catalog = load_skill_catalog(path)
    choice = propose_skill_from_curiosity(
        Core(model), catalog=catalog, session_uuid=session)
    assert choice["status"] == "proposed"
    assert choice["question_id"] == question_id
    assert choice["skill_id"] == "double"
    assert len(model.calls) == 1
    assert "holdout_project" not in model.calls[0][0]
    assert "test_double.py" not in model.calls[0][0]
    cycle = GoalCycle({"run_experiment": handler(root, path, model)})
    receipt = cycle.poll_due()[0]
    assert receipt["status"] == "success"
    result = json.loads(cycle.history()[0]["result_json"])
    assert result["created_executable_code"] is True
    assert result["skill_promotion_ready"] is True
    assert len(model.calls) == 2
    # Persistent prior trial suppresses repeated model prompts and execution.
    later = propose_skill_from_curiosity(
        Core(model), catalog=catalog, session_uuid=begin_session())
    assert later["reason"] == "no_unattempted_skills"
    assert len(model.calls) == 2
    assert GoalCycle({"run_experiment": handler(root, path, model)}).poll_due() == []


def test_no_curiosity_is_an_explicit_abstention_without_model_call(world):
    _, session, path = world
    model = ModelThatSelectsAndWrites(1)
    answer = propose_skill_from_curiosity(
        Core(model), catalog=load_skill_catalog(path), session_uuid=session)
    assert answer == {"status": "n/a", "reason": "no_open_curiosity"}
    assert model.calls == []


def test_invalid_or_unrelated_model_choice_does_not_create_goals(world):
    root, session, path = world
    question_id = insert_curiosity("Could symbolic arithmetic help us reason?")
    catalog = load_skill_catalog(path)
    for fake_id in ("outside_catalog", None):
        model = ModelThatSelectsAndWrites(question_id, skill_id=fake_id)
        outcome = propose_skill_from_curiosity(
            Core(model), catalog=catalog, session_uuid=session)
        assert outcome["status"] != "proposed"
    assert get_store().fetchall(
        "SELECT * FROM cognition_goal_proposals WHERE action_type='run_experiment'") == []


def test_model_may_refuse_skill_and_preserve_curiosity(world):
    _, session, path = world
    question_id = insert_curiosity("What is the meaning of this poetry?")
    model = ModelThatSelectsAndWrites(question_id, skill_id=None)
    result = propose_skill_from_curiosity(
        Core(model), catalog=load_skill_catalog(path), session_uuid=session)
    assert result["status"] == "unverified"
    assert get_store().fetchall(
        "SELECT * FROM cognition_goal_proposals WHERE action_type='run_experiment'") == []
