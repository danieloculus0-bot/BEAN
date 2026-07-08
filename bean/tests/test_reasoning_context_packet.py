"""Reasoning context packet coverage tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from bean.memory.identity import bootstrap_identity
from bean.memory.origin import ensure_origin_records
from bean.memory.session import begin_session
from bean.memory.event_logger import EventType, Source, log_event
from bean.memory.store import _local, get_store, init_store


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    tmpdir = Path(tempfile.mkdtemp())
    init_store(str(tmpdir / "context_packet.db"))
    bootstrap_identity()
    session_uuid = begin_session()
    ensure_origin_records(session_uuid)
    return session_uuid


def test_context_packet_has_core_sections_and_ids():
    session_uuid = make_db()
    event_id = log_event(session_uuid, EventType.HUMAN_INPUT, "Supervisor requested status review.", Source.HUMAN)

    from bean.world.claim import Claim, ClaimCategory, ClaimSource
    from bean.world.model_store import ModelStore
    ModelStore().save(Claim(key="test.status", content="BEAN is under test.", category=ClaimCategory.SELF, source_type=ClaimSource.BOOTSTRAP, confidence=0.9))

    from bean.wisdom.activation_engine import WisdomActivationEngine
    WisdomActivationEngine().process_event(session_uuid, "Plan changed and remains uncertain.", event_id, {"stated_reason": "capacity"})

    from bean.speculation import init_speculation
    init_speculation().create_hypothesis(session_uuid, "This may need follow up.", claim_type="hypothesis", evidence_level="hypothetical")

    from bean.reasoning.context_builder import build_reasoning_context
    packet = build_reasoning_context(session_uuid, source_event_id=event_id)
    context = packet["context"]

    for key in ["identity", "origin_covenant", "active_boundaries", "capabilities", "recent_events", "active_world_claims", "wisdom_recent_traces", "speculative_summary"]:
        assert key in context

    assert context["identity_rules"]["llm_is_tool_not_identity"] is True
    assert context["body_output_status"]["enabled"] is False
    assert len(context["active_boundaries"]) >= 1
    assert len(context["capabilities"]) >= 1
    assert len(context["recent_events"]) >= 1
    assert len(context["active_world_claims"]) >= 1
    assert len(context["wisdom_recent_traces"]) >= 1

    row = get_store().fetchone("SELECT included_event_ids_json, included_claim_ids_json, included_wisdom_trace_ids_json FROM reasoning_context_packets WHERE packet_id=?", (packet["packet_id"],))
    assert json.loads(row["included_event_ids_json"])
    assert json.loads(row["included_claim_ids_json"])
    assert json.loads(row["included_wisdom_trace_ids_json"])


if __name__ == "__main__":
    try:
        test_context_packet_has_core_sections_and_ids()
        print("PASS test_context_packet_has_core_sections_and_ids")
    except Exception:
        print("FAIL test_context_packet_has_core_sections_and_ids")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
