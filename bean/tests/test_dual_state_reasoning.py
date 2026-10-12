"""Dual-state reasoning must preserve uncertainty, provenance, and context."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from bean.cognition.dual_state import DualStateReasoner


def new_reasoner():
    conn = sqlite3.connect(":memory:")
    return DualStateReasoner(conn)


def test_undecided_is_not_a_negative_claim():
    r = new_reasoner()
    result = r.open_case("rule", "rule A", "rule B")
    assert result["status"] == "unknown"
    assert result["selected"] is None
    assert result["action_authorized"] is False


def test_same_source_cannot_win_by_repetition():
    r = new_reasoner()
    r.open_case("rule", "A", "B")
    for i in range(5):
        result = r.add_evidence(
            "rule", evidence_ref=f"a{i}", source_id="one-origin",
            side="a", observation="same report",
        )
    assert result["status"] == "insufficient_evidence"
    assert result["independent_sources"] == {"a": 1, "b": 0}


def test_two_independent_sources_support_provisionally_and_conflicts_remain():
    r = new_reasoner()
    r.open_case("rule", "A", "B")
    r.add_evidence("rule", evidence_ref="a1", source_id="sensor",
                   side="a", observation="A measured")
    result = r.add_evidence("rule", evidence_ref="a2", source_id="reviewer",
                            side="a", observation="A confirmed")
    assert result["status"] == "supported_a"
    assert result["selected"] == "a"
    result = r.add_evidence("rule", evidence_ref="b1", source_id="instrument",
                            side="b", observation="B contradicts")
    assert result["status"] == "contested"
    assert result["selected"] is None
    assert len(result["evidence"]) == 3


def test_context_isolation_does_not_rewrite_prior_learning():
    r = new_reasoner()
    r.open_case("rule", "old A", "new B")
    for idx, side, ctx in [(1, "a", "old"), (2, "a", "old"),
                           (3, "b", "new"), (4, "b", "new")]:
        r.add_evidence("rule", evidence_ref=str(idx), source_id=f"src{idx}",
                       side=side, context=ctx, observation=f"{side} seen")
    assert r.evaluate("rule")["status"] == "context_required"
    assert r.evaluate("rule", context="old")["status"] == "supported_a"
    assert r.evaluate("rule", context="new")["status"] == "supported_b"
    assert r.evaluate("rule", context="unknown")["status"] == "unknown"
    assert r.contexts("rule") == ["new", "old"]


def test_idempotent_evidence_and_redefinition_rejected():
    r = new_reasoner()
    r.open_case("rule", "A", "B")
    kwargs = dict(evidence_ref="e1", source_id="s1", side="a",
                  observation="A happened")
    r.add_evidence("rule", **kwargs)
    assert r.add_evidence("rule", **kwargs)["evidence_count"] == 1
    with pytest.raises(ValueError):
        r.add_evidence("rule", **{**kwargs, "side": "b"})
    with pytest.raises(ValueError):
        r.open_case("rule", "B", "A")
    assert r.evaluate("rule")["evidence_count"] == 1


def test_restarts_keep_both_claims_and_all_evidence():
    with tempfile.TemporaryDirectory() as temp:
        path = str(Path(temp) / "dual.db")
        conn = sqlite3.connect(path)
        r = DualStateReasoner(conn)
        r.open_case("rule", "A", "B")
        r.add_evidence("rule", evidence_ref="a1", source_id="s1",
                       side="a", observation="A")
        r.add_evidence("rule", evidence_ref="b1", source_id="s2",
                       side="b", observation="B")
        old = r.evaluate("rule")
        conn.close()
        conn = sqlite3.connect(path)
        fresh = DualStateReasoner(conn)
        assert fresh.evaluate("rule") == old
        conn.close()


def test_invalid_evidence_and_bad_threshold_cannot_fake_certainty():
    r = new_reasoner()
    r.open_case("rule", "A", "B")
    with pytest.raises(ValueError):
        r.add_evidence("rule", evidence_ref="e", source_id="",
                       side="a", observation="fake")
    with pytest.raises(ValueError):
        r.add_evidence("rule", evidence_ref="e", source_id="s",
                       side="c", observation="fake")
    with pytest.raises(ValueError):
        r.evaluate("rule", min_independent_sources=1)
    with pytest.raises(KeyError):
        r.evaluate("missing")


def test_host_adapter_exposes_dual_state_method():
    from bean.integration.reasoning_layer import BeanReasoningLayer
    assert hasattr(BeanReasoningLayer, "dual_state")
