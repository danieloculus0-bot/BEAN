"""Regression tests for observation-to-reasoning and knowledge correctness.

These tests use local SQLite and mock adapters; no cloud access is required.
"""
from bean.cognition.consolidation import ConsolidationEngine
from bean.memory.event_logger import EventType, Source, log_event
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.store import get_store, init_store
from bean.reasoning.context_builder import build_reasoning_context
from bean.reasoning.prompt_builder import build_ollama_prompt
from bean.reasoning.reasoning_engine import ReasoningEngine


def _start(tmp_path):
    init_store(str(tmp_path / "learning-flow.db"))
    bootstrap_identity()
    return begin_session()


def _question(question):
    store = get_store()
    cursor = store.execute(
        "INSERT INTO curiosity(question, context) VALUES (?, ?)",
        (question, "regression test"),
    )
    store.commit()
    return cursor.lastrowid


def test_unrelated_fact_does_not_answer_question(tmp_path):
    session = _start(tmp_path)
    question_id = _question("Why did the motor controller overheat?")
    log_event(
        session, EventType.FACT_LEARNED,
        "The motor controller has a blue housing.", Source.SYSTEM,
    )

    assert ConsolidationEngine()._close_resolved_questions(session) == 0
    question = get_store().fetchone(
        "SELECT status, answer FROM curiosity WHERE id=?", (question_id,),
    )
    assert question["status"] == "open"
    assert question["answer"] is None


def test_linked_fact_answers_only_its_question(tmp_path):
    session = _start(tmp_path)
    target_id = _question("Why did the controller overheat?")
    unrelated_id = _question("When was the controller installed?")
    answer = "The cooling fan stopped, as recorded in the maintenance event."
    log_event(
        session, EventType.FACT_LEARNED, "Controller root cause investigated.",
        Source.SYSTEM, data={"question_id": target_id, "answer": answer},
    )

    engine = ConsolidationEngine()
    assert engine._close_resolved_questions(session) == 1
    assert engine._close_resolved_questions(session) == 0
    answered = get_store().fetchone(
        "SELECT status, answer FROM curiosity WHERE id=?", (target_id,),
    )
    unresolved = get_store().fetchone(
        "SELECT status FROM curiosity WHERE id=?", (unrelated_id,),
    )
    assert answered["status"] == "answered"
    assert answered["answer"] == answer
    assert unresolved["status"] == "open"


def test_structured_observation_reaches_offline_reasoning(tmp_path):
    session = _start(tmp_path)
    source_id = log_event(
        session, EventType.OBSERVATION, "Controller thermal reading.",
        Source.SYSTEM, data={"controller": "A", "temperature_c": 87},
    )
    packet = build_reasoning_context(session, source_event_id=source_id)
    event = next(
        item for item in packet["context"]["recent_events"]
        if item["id"] == source_id
    )
    assert event["data"] == {"controller": "A", "temperature_c": 87}
    prompt = build_ollama_prompt(packet["context"])
    assert '"temperature_c":87' in prompt


def test_provider_failure_is_not_success(tmp_path):
    session = _start(tmp_path)

    class OfflineUnavailable:
        adapter_name = "offline_fixture"
        model_name = "unavailable"

        def complete(self, prompt, context):
            return {"ok": False, "error": "model unavailable"}

    report = ReasoningEngine(adapter=OfflineUnavailable()).run(session)
    assert report["success"] is False
    assert report["structured_response_valid"] is False
    assert report["filter_passed"] is False
    assert report["proposal_id"]


def test_valid_mock_reasoning_still_succeeds(tmp_path):
    session = _start(tmp_path)
    report = ReasoningEngine().run(session, adapter_name="mock")
    assert report["success"] is True
    assert report["structured_response_valid"] is True


def test_local_reasoning_keeps_technical_vocabulary(tmp_path):
    import json

    session = _start(tmp_path)

    class TechnicalMock:
        adapter_name = "offline_fixture"
        model_name = "technical_test"

        def complete(self, prompt, context):
            return {"ok": True, "raw_text": json.dumps({
                "summary": "The servo actuator is uncertain; do not move it.",
                "observations": [],
                "interpretations": [],
                "assumptions": [],
                "uncertainties": [],
                "evidence_refs": [],
                "candidate_steps": [],
                "risk_flags": [],
                "confidence": 0.5,
            })}

    report = ReasoningEngine(adapter=TechnicalMock()).run(session)
    assert report["success"] is True
    assert report["filter_passed"] is True


def test_local_reasoning_retains_prior_trial_even_after_many_new_events(tmp_path):
    session = _start(tmp_path)
    recorded = log_event(
        session, EventType.OBSERVATION,
        "Earlier cognitive trial gave feedback.",
        Source.SYSTEM, subtype="cognitive_module_experiment",
        data={"run_id": "older_experiment_receipt_123", "reward": -1},
    )
    for index in range(6):
        log_event(
            session, EventType.OBSERVATION,
            f"Later unrelated event {index}.", Source.SYSTEM,
            data={"index": index},
        )
    context = build_reasoning_context(session)["context"]
    assert recorded in [e["id"] for e in context["recent_events"]]
    prompt = build_ollama_prompt(context)
    assert "older_experiment_receipt_123" in prompt
    assert "Later unrelated event 5" in prompt
    assert prompt.count("older_experiment_receipt_123") == 1


def test_repeated_question_review_does_not_duplicate_pending_goals(tmp_path):
    from bean.cognition.goal_state import GoalStateEngine
    session = _start(tmp_path)
    qid = _question("Can BEAN investigate this unanswered question?")
    row = dict(get_store().fetchone("SELECT * FROM curiosity WHERE id=?", (qid,)))
    engine = GoalStateEngine()
    first = engine.propose(session, [], [row])
    second = engine.propose(session, [], [row])
    assert len(first) == 1
    assert second == []
    assert len(engine.get_pending(session)) == 1
