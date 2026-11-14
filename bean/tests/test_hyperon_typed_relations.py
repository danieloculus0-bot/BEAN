"""BEAN Hyperon-inspired typed inference, synthetic facts and exact proofs."""
import json

import pytest

from bean.cognition.typed_relations import TypedRelations
from bean.memory.store import get_store, init_store
from bean.memory.identity import bootstrap_identity
from bean.memory.origin import ensure_origin_records
from bean.memory.session import begin_session
from bean.memory.event_logger import EventType, Source, log_event
from bean.reasoning.context_builder import build_reasoning_context
from bean.reasoning.prompt_builder import build_ollama_prompt
from bean.runtime.inbox_handlers import make_handlers
from bean.runtime.inbox import InboxMessage
from bean.world.model_store import ModelStore


@pytest.fixture
def bean(tmp_path):
    path = tmp_path / "bean-typed.sqlite3"
    init_store(str(path))
    bootstrap_identity()
    session = begin_session()
    ensure_origin_records(session)
    yield path, session
    get_store().close()


def edge(engine, left, right, *, predicate="located_in", polarity="support",
         evidence="receipt:synthetic", confidence=0.7):
    return engine.observe(
        subject=left, predicate=predicate, target=right,
        polarity=polarity, source_ref=f"source:{left}-{right}",
        evidence_refs=[evidence], confidence=confidence,
    )


def test_two_hop_query_has_explainable_proof_and_no_implicit_claims(bean):
    db, session = bean
    r = TypedRelations()
    first = edge(r, "sample", "bin", evidence="receipt:one")
    second = edge(r, "bin", "warehouse", evidence="receipt:two", confidence=0.4)
    before = get_store().fetchone(
        "SELECT count(*) AS n FROM world_claims")["n"]
    answer = r.query(subject="sample", predicate="located_in", target="warehouse")
    assert answer["status"] == "inferred_unverified"
    assert answer["world_truth_verified"] is False
    assert answer["rule"] == "homogeneous_transitive_v1"
    proof = answer["results"][0]
    assert proof["hops"] == 2
    assert proof["inferred"] is True
    assert proof["evidence_claim_ids"] == [first["claim_id"], second["claim_id"]]
    assert proof["minimum_source_confidence"] == pytest.approx(0.4)
    assert [p["evidence_refs"] for p in proof["proof"]] == [
        ["receipt:one"], ["receipt:two"]]
    assert get_store().fetchone(
        "SELECT count(*) AS n FROM world_claims")["n"] == before


def test_three_hops_and_reverse_direction_does_not_autocomplete(bean):
    _, session = bean
    r = TypedRelations()
    edge(r, "a", "b")
    edge(r, "b", "c")
    edge(r, "c", "d")
    assert r.query(subject="a", predicate="located_in",
                   target="d", max_hops=3)["results"][0]["hops"] == 3
    assert r.query(subject="a", predicate="located_in",
                   target="d", max_hops=2)["status"] == "unknown"
    assert r.query(subject="d", predicate="located_in",
                   target="a")["status"] == "unknown"


def test_nonstransitive_relations_never_chain(bean):
    _, session = bean
    r = TypedRelations()
    edge(r, "a", "b", predicate="related_to")
    edge(r, "b", "c", predicate="related_to")
    assert r.query(subject="a", predicate="related_to",
                   target="b")["status"] == "direct_unverified"
    assert r.query(subject="a", predicate="related_to",
                   target="c")["status"] == "unknown"


def test_different_predicates_never_mix_into_false_conclusion(bean):
    _, session = bean
    r = TypedRelations()
    edge(r, "axle", "machine", predicate="part_of")
    edge(r, "machine", "building", predicate="located_in")
    assert r.query(subject="axle", predicate="part_of",
                   target="building")["status"] == "unknown"
    assert r.query(subject="axle", predicate="located_in",
                   target="building")["status"] == "unknown"


def test_refutation_blocks_an_inferred_path_and_is_visible(bean):
    _, session = bean
    r = TypedRelations()
    edge(r, "a", "b", evidence="receipt:one")
    edge(r, "b", "c", evidence="receipt:two")
    before = r.query(subject="a", predicate="located_in", target="c")
    assert before["status"] == "inferred_unverified"
    edge(r, "b", "c", polarity="refute", evidence="receipt:contradiction")
    after = r.query(subject="a", predicate="located_in", target="c")
    assert after["status"] == "unknown"
    contested = r.query(subject="b", predicate="located_in", target="c")
    assert contested["status"] == "contested"
    assert contested["results"][0]["counterevidence"]["polarity"] == "refute"


def test_direct_refutation_does_not_prove_negation(bean):
    _, session = bean
    r = TypedRelations()
    edge(r, "a", "b", polarity="refute")
    output = r.query(subject="a", predicate="is_a", target="b")
    assert output["status"] == "unknown"  # other predicate
    output = r.query(subject="a", predicate="located_in", target="b")
    assert output["status"] == "refuted_unverified"
    assert output["results"][0]["independent_validation"] is False


def test_circular_relation_does_not_infer_self(bean):
    _, session = bean
    r = TypedRelations()
    edge(r, "a", "b")
    edge(r, "b", "c")
    edge(r, "c", "a")
    got = r.query(subject="a", predicate="located_in", max_hops=4)
    assert {x["target"] for x in got["results"]} == {"b", "c"}
    assert all(x["target"] != "a" for x in got["results"])


def test_historical_revision_preserved_with_unchanged_active_edge(bean):
    _, session = bean
    r = TypedRelations()
    original = edge(r, "a", "b", evidence="receipt:old")
    revised = edge(r, "a", "b", evidence="receipt:new")
    assert original["claim_id"] != revised["claim_id"]
    history = ModelStore().get_history(
        "symbolic.located_in.a.b.support")
    assert len(history) == 2
    assert not history[0].active
    assert history[1].active
    proof = r.query(subject="a", predicate="located_in", target="b")["results"][0]["proof"]
    assert proof[0]["claim_id"] == revised["claim_id"]
    assert proof[0]["evidence_refs"] == ["receipt:new"]


def test_restart_does_not_lose_source_proofs(bean):
    path, session = bean
    r = TypedRelations()
    a = edge(r, "part", "assembly")
    b = edge(r, "assembly", "machine")
    get_store().close()
    init_store(str(path))
    r2 = TypedRelations()
    output = r2.query(subject="part", predicate="part_of", target="machine")
    assert output["status"] == "inferred_unverified"
    assert output["results"][0]["evidence_claim_ids"] == [a["claim_id"], b["claim_id"]]


def test_bounded_incomplete_graph_does_not_return_partial_answer(bean):
    _, session = bean
    r = TypedRelations()
    edge(r, "a", "b")
    edge(r, "b", "c")
    report = r.query(subject="a", predicate="located_in", target="c",
                     max_records=1)
    assert report["status"] == "incomplete_graph"
    assert report["truncated"] is True
    assert report["results"] == []


def test_absence_does_not_become_false_and_invalid_claims_are_rejected(bean):
    _, session = bean
    r = TypedRelations()
    assert r.query(subject="a", predicate="is_a", target="b")["status"] == "unknown"
    with pytest.raises(ValueError):
        edge(r, "a", "b", predicate="is_like")
    with pytest.raises(ValueError):
        edge(r, "a", "a")
    with pytest.raises(ValueError):
        r.observe(subject="a", predicate="is_a", target="b",
                  source_ref="", evidence_refs=["receipt:one"])
    with pytest.raises(ValueError):
        r.observe(subject="a", predicate="is_a", target="b",
                  source_ref="source:a", evidence_refs=["receipt:one", "receipt:one"])
    assert get_store().fetchone(
        "SELECT count(*) AS n FROM world_claims WHERE key LIKE 'symbolic.%'")["n"] == 0


def test_runtime_inbox_asserts_and_queries_real_model(bean):
    _, session = bean
    handlers = make_handlers()
    first = handlers["assert_symbolic_relation"](
        InboxMessage("assert_symbolic_relation", {
            "subject": "nut", "predicate": "part_of", "target": "assembly",
            "source_ref": "fixture:one", "evidence_refs": ["fixture:case1"],
        }), session)
    assert first["success"] is True
    second = handlers["assert_symbolic_relation"](
        InboxMessage("assert_symbolic_relation", {
            "subject": "assembly", "predicate": "part_of", "target": "vehicle",
            "source_ref": "fixture:two", "evidence_refs": ["fixture:case2"],
        }), session)
    output = handlers["query_symbolic_relation"](
        InboxMessage("query_symbolic_relation", {
            "subject": "nut", "predicate": "part_of", "target": "vehicle"
        }), session)
    assert output["inference"]["status"] == "inferred_unverified"
    assert len(output["inference"]["results"][0]["proof"]) == 2
    assert all(x["success"] for x in (first, second, output))


def test_structured_question_populates_reasoning_context_and_ollama_prompt(bean):
    _, session = bean
    r = TypedRelations()
    first = edge(r, "a", "b")
    second = edge(r, "b", "c")
    event_id = log_event(
        session, EventType.HUMAN_INPUT, "What contains a?",
        Source.HUMAN, data={
            "symbolic_query": {
                "subject": "a", "predicate": "located_in", "target": "c"
            }
        })
    packet = build_reasoning_context(session, source_event_id=event_id)
    inference = packet["context"]["symbolic_inference"]
    assert inference["status"] == "inferred_unverified"
    included = json.loads(get_store().fetchone(
        "SELECT included_claim_ids_json FROM reasoning_context_packets "
        "WHERE packet_id=?", (packet["packet_id"],)
    )["included_claim_ids_json"])
    assert set(inference["results"][0]["evidence_row_ids"]).issubset(included)
    compact = build_ollama_prompt(packet["context"])
    assert first["claim_id"] in compact
    assert second["claim_id"] in compact
    assert '"world_truth_verified":false' in compact


def test_malformed_question_is_reported_as_invalid_not_invented_fact(bean):
    _, session = bean
    event = log_event(
        session, EventType.HUMAN_INPUT, "Check invalid symbolic query",
        Source.HUMAN, data={"symbolic_query": {"subject": "a", "predicate": "nonsense"}})
    packet = build_reasoning_context(session, source_event_id=event)
    assert packet["context"]["symbolic_inference"]["status"] == "invalid_structured_query"
