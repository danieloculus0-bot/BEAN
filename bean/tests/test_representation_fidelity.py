"""BEAN representation audit: evidence integrity from Core to strict JSON ports.

No new cognitive mechanisms, default interpretation policies, or altered
historical SQLite rows are introduced by these tests.
"""
from __future__ import annotations

import json
import math

import pytest

from bean.memory.audit_mirror import mirror_path
from bean.memory.event_logger import (
    EventType, Source, get_recent_events, log_event, parse_event_data,
)
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.store import get_store, init_store
from bean.modules.builtin import memory_recall
from bean.reasoning.context_builder import build_reasoning_context


def _reject_constant(value):
    raise ValueError("Non-standard JSON number: " + value)


def test_nonfinite_observations_are_portable_without_imputation(tmp_path):
    path = tmp_path / "evidence.sqlite"
    init_store(str(path))
    bootstrap_identity()
    session = begin_session()
    original = {
        "sensor": "fixture-1",
        "samples": [1.25, float("nan"), float("inf"), -float("inf"), None],
        "nested": {"uncertainty": float("nan"), "quality": "provisional"},
        "count": 9007199254740993,
    }
    event_id = log_event(
        session, EventType.OBSERVATION, "Fictional sensor observation.",
        Source.SENSOR, data=original,
    )
    assert math.isnan(original["samples"][1])
    row = next(x for x in get_recent_events(session) if x["id"] == event_id)
    raw = json.loads(row["data"], parse_constant=_reject_constant)
    assert raw["samples"] == [
        1.25, {"$bean_nonfinite_float": "nan"},
        {"$bean_nonfinite_float": "+inf"},
        {"$bean_nonfinite_float": "-inf"}, None,
    ]
    assert raw["nested"]["uncertainty"] == {"$bean_nonfinite_float": "nan"}
    assert raw["count"] == 9007199254740993

    # The append-only JSONL audit mirror is parseable by any strict JSON
    # implementation; no free-floating NaN token leaks to downstream tools.
    mirror = mirror_path(path)
    for line in mirror.read_text(encoding="utf-8").splitlines():
        json.loads(line, parse_constant=_reject_constant)

    recall = memory_recall({"session_uuid": session, "limit": 30}, {})
    observed = next(x for x in recall["events"] if x["id"] == event_id)
    assert observed["data"] == raw
    json.dumps(recall, allow_nan=False)
    reasoning = build_reasoning_context(session, source_event_id=event_id)
    event = next(
        x for x in reasoning["context"]["recent_events"] if x["id"] == event_id
    )
    assert event["data"] == raw
    json.dumps(reasoning["context"], allow_nan=False)
    get_store().close()


def test_legacy_nonstandard_json_is_normalized_only_on_read():
    historical = '{"older_sensor":[NaN,Infinity,-Infinity],"legit":null}'
    observed = parse_event_data(historical)
    assert observed["older_sensor"] == [
        {"$bean_nonfinite_float": "nan"},
        {"$bean_nonfinite_float": "+inf"},
        {"$bean_nonfinite_float": "-inf"},
    ]
    assert observed["legit"] is None
    assert json.dumps(observed, allow_nan=False)
    # Legacy source remains unchanged; no implicit migration or mirror rewrite.
    assert "NaN" in historical and "-Infinity" in historical


def test_finite_json_cases_have_no_behavior_change(tmp_path):
    init_store(str(tmp_path / "finite.sqlite"))
    bootstrap_identity()
    session = begin_session()
    values = {"number": 1.2345, "bool": True, "nothing": None,
              "list": [0, -0.0, "é", {"relation_id": "q-42"}]}
    event_id = log_event(session, EventType.OBSERVATION,
                         "Finite fixture.", Source.SYSTEM, data=values)
    row = next(x for x in get_recent_events(session) if x["id"] == event_id)
    assert json.loads(row["data"], parse_constant=_reject_constant) == values
    get_store().close()
