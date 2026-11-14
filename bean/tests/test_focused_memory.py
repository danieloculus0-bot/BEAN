"""Focused retrieval of real versioned BEAN world-memory, all synthetic."""
import json

import pytest

from bean.memory.store import get_store, init_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.event_logger import log_event, EventType, Source
from bean.memory.focused_recall import recall_focused_claims
from bean.world.claim import make_claim, ClaimCategory, ClaimSource
from bean.world.model_store import ModelStore
from bean.reasoning.context_builder import build_reasoning_context
from bean.reasoning.prompt_builder import build_ollama_prompt


@pytest.fixture
def core(tmp_path):
    path = tmp_path / "bean.sqlite3"
    init_store(str(path))
    bootstrap_identity()
    session = begin_session()
    ModelStore()
    yield path, session
    get_store().close()


def claim(key, text, *, confidence=0.6, source_ref=None, evidence=None):
    value = make_claim(
        key, text, ClaimCategory.ENVIRONMENT, ClaimSource.SUPERVISOR,
        confidence, source_ref=source_ref, evidence=evidence)
    ModelStore().save(value)
    return value


def test_old_relevant_claim_survives_top20_truncation(core):
    _, session = core
    old = claim("environment.induction.voltage", "Induction voltage is 17.6 V",
                confidence=0.3, source_ref="synthetic:bench-17",
                evidence=["test:measured-17"])
    for n in range(50):
        claim(f"environment.general.item.{n}",
              "Unrelated ordinary telemetry inspection reading",
              confidence=0.99)
    event = log_event(session, EventType.HUMAN_INPUT,
                      "Review induction voltage reading", Source.HUMAN)
    packet = build_reasoning_context(session, source_event_id=event)
    focus = packet["context"]["focused_world_memory"]
    assert focus and focus[0]["claim_id"] == old.claim_id
    assert focus[0]["source_ref"] == "synthetic:bench-17"
    assert focus[0]["evidence_refs"] == ["test:measured-17"]
    assert focus[0]["evidence_independently_authenticated"] is False
    assert all(row["claim_id"] != old.claim_id
               for row in packet["context"]["active_world_claims"])
    included = json.loads(get_store().fetchone(
        "SELECT included_claim_ids_json FROM reasoning_context_packets "
        "WHERE packet_id=?", (packet["packet_id"],)
    )["included_claim_ids_json"])
    assert focus[0]["source_row_id"] in included
    prompt = build_ollama_prompt(packet["context"])
    assert "Induction voltage is 17.6 V" in prompt
    assert old.claim_id in prompt


def test_revisions_use_new_claim_not_superseded_version(core):
    _, session = core
    original = claim("environment.induction.voltage", "Induction voltage is 12 V")
    event = log_event(session, EventType.HUMAN_INPUT,
                      "Check induction voltage", Source.HUMAN)
    newer = claim("environment.induction.voltage", "Induction voltage is 14 V",
                  source_ref="synthetic:followup")
    focus = build_reasoning_context(session, source_event_id=event)["context"]["focused_world_memory"]
    assert len(focus) == 1
    assert focus[0]["claim_id"] == newer.claim_id
    assert focus[0]["previous_claim_id"] == original.claim_id
    assert "14 V" in focus[0]["content"]
    assert "12 V" not in focus[0]["content"]
    history = ModelStore().get_history("environment.induction.voltage")
    assert len(history) == 2 and history[0].active is False


def test_restart_keeps_relevance_and_revision_links(core):
    path, session = core
    previous = claim("environment.sensor.latency", "Sensor latency 12 ms")
    current = claim("environment.sensor.latency", "Sensor latency 8 ms")
    get_store().close()
    init_store(str(path))
    found = recall_focused_claims(get_store()._conn(), "sensor latency")
    assert len(found) == 1
    assert found[0]["claim_id"] == current.claim_id
    assert found[0]["previous_claim_id"] == previous.claim_id


def test_missing_or_unrelated_evidence_is_unknown_not_recalled(core):
    claim("environment.tool.temp", "Temperature unknown")
    conn = get_store()._conn()
    assert recall_focused_claims(conn, "rare geological glacier") == []
    assert recall_focused_claims(conn, "with the would") == []


def test_retrieval_is_bounded_and_lexical_not_truth_proof(core):
    for i in range(20):
        claim(f"environment.induction.test{i}",
              "Induction voltage reported by source", confidence=0.9)
    conn = get_store()._conn()
    found = recall_focused_claims(conn, "induction voltage", limit=3)
    assert len(found) == 3
    assert all(entry["evidence_independently_authenticated"] is False
               for entry in found)
    with pytest.raises(ValueError):
        recall_focused_claims(conn, "induction voltage", limit=0)
    with pytest.raises(TypeError):
        recall_focused_claims(conn, None)
