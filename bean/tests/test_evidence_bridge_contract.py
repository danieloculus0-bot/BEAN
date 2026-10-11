"""Test evidence-to-Core learning across restarts and adversarial sources."""
from __future__ import annotations
import pytest
from bean.integration.reasoning_layer import BeanReasoningLayer
from bean.integration.evidence_bridge import EvidenceBridge, SourceClaim
from bean.memory.store import get_store

TIME = "2026-10-10T12:00:00Z"


def item(id, round_id, origin, value, verified=True):
    return SourceClaim(
        record_id=id, round_id=round_id, origin=origin,
        source_ref=f"fixture:{round_id}:{id}", value=value,
        verified=verified,
        verification_ref=f"independent:{round_id}:{id}" if verified else None,
        observed_at=TIME,
    )


def test_revision_survives_multiple_restarts(tmp_path):
    path = str(tmp_path / "core.sqlite")
    with BeanReasoningLayer(path) as layer:
        bridge = EvidenceBridge(layer)
        assert bridge.start("round_alpha", "calibration_code", "What is the code?")["new"]
        assert not bridge.start("round_alpha", "calibration_code", "What is the code?")["new"]
        bridge.observe(item("lab_one", "round_alpha", "source_one", "HX-100"))
        bridge.observe(item("lab_two", "round_alpha", "source_two", "HX-100"))
        first = bridge.finalize("round_alpha")
        assert first["status"] == "confirmed"
        assert first["execution_permission"] == "none"
        assert bridge.finalize("round_alpha") == first
        assert bridge.current("calibration_code")["value"] == "HX-100"
        assert get_store().fetchone(
            "SELECT COUNT(*) AS n FROM epistemic_audits WHERE candidate_key=?",
            ("external.research.calibration_code",),
        )["n"] == 1
    with BeanReasoningLayer(path) as layer:
        bridge = EvidenceBridge(layer)
        assert bridge.current("calibration_code")["value"] == "HX-100"
        bridge.start("round_beta", "calibration_code", "Did calibration change?")
        bridge.observe(item("new_one", "round_beta", "source_three", "HX-200"))
        bridge.observe(item("new_two", "round_beta", "source_four", "HX-200"))
        second = bridge.finalize("round_beta")
        assert second["status"] == "revised"
        assert second["previous_value"] == "HX-100"
        assert [v["value"] for v in bridge.history("calibration_code")] == ["HX-100", "HX-200"]
    with BeanReasoningLayer(path) as layer:
        bridge = EvidenceBridge(layer)
        assert bridge.current("calibration_code")["value"] == "HX-200"
        assert not bridge.pending()


def test_disagreement_reopens_current_claim(tmp_path):
    with BeanReasoningLayer(str(tmp_path / "disagree.db")) as layer:
        bridge = EvidenceBridge(layer)
        bridge.start("round_known", "inspection_state", "Current inspection?")
        bridge.observe(item("one", "round_known", "lab_one", "complete"))
        bridge.observe(item("two", "round_known", "lab_two", "complete"))
        bridge.finalize("round_known")
        bridge.start("round_dispute", "inspection_state", "Any change?")
        bridge.observe(item("three", "round_dispute", "lab_one", "complete"))
        bridge.observe(item("four", "round_dispute", "lab_two", "incomplete"))
        result = bridge.finalize("round_dispute")
        assert result["status"] == "contested"
        assert result["value"] is None
        assert bridge.current("inspection_state") is None
        assert bridge.history("inspection_state")[0]["value"] == "complete"
        assert len(bridge.garden.open_uncertainties()) == 1


def test_echo_and_unverified_claims_do_not_vote(tmp_path):
    with BeanReasoningLayer(str(tmp_path / "echo.db")) as layer:
        bridge = EvidenceBridge(layer)
        bridge.start("round_echo", "sensor_state", "Did the sensor trip?")
        first = item("wire_first", "round_echo", "syndicated_wire", "yes")
        assert bridge.observe(first)
        assert not bridge.observe(first)
        bridge.observe(item("wire_copy", "round_echo", "syndicated_wire", "yes"))
        bridge.observe(item("unverified", "round_echo", "other_source", "yes", False))
        result = bridge.finalize("round_echo")
        assert result["status"] == "insufficient"
        assert result["distinct_origins"] == 1
        assert bridge.current("sensor_state") is None


def test_idempotent_record_rejects_mutated_payload_and_duplicate_ref(tmp_path):
    with BeanReasoningLayer(str(tmp_path / "duplicates.db")) as layer:
        bridge = EvidenceBridge(layer)
        bridge.start("round_replay", "part_quality", "Passes?")
        old = item("inspect_one", "round_replay", "lab_one", "pass")
        bridge.observe(old)
        with pytest.raises(ValueError, match="different evidence"):
            bridge.observe(item("inspect_one", "round_replay", "lab_one", "fail"))
        with pytest.raises(ValueError, match="duplicate"):
            bridge.observe(SourceClaim("inspect_two", "round_replay", "lab_two",
                                      old.source_ref, "pass", True, "verifier:new", TIME))
        assert bridge.db.execute("SELECT COUNT(*) FROM bridge_evidence_inputs").fetchone()[0] == 1


def test_untrusted_verification_and_closed_round_fail_closed(tmp_path):
    with BeanReasoningLayer(str(tmp_path / "invalid.db")) as layer:
        bridge = EvidenceBridge(layer)
        bridge.start("round_invalid", "motor_status", "Running?")
        with pytest.raises(ValueError, match="verification_ref"):
            SourceClaim("bad_one", "round_invalid", "origin_one", "ref:a",
                        "yes", True, None, TIME)
        with pytest.raises(ValueError, match="independently"):
            SourceClaim("bad_two", "round_invalid", "origin_one", "ref:b",
                        "yes", True, "ref:b", TIME)
        with pytest.raises(ValueError, match="explicitly boolean"):
            SourceClaim("bad_three", "round_invalid", "origin_one", "ref:c",
                        "yes", 1, "verify:c", TIME)
        assert bridge.finalize("round_invalid")["status"] == "insufficient"
        with pytest.raises(ValueError, match="finalized"):
            bridge.observe(item("too_late", "round_invalid", "origin_one", "yes"))


def test_host_reasoning_and_evidence_do_not_enable_actions(tmp_path):
    with BeanReasoningLayer(str(tmp_path / "safe.db")) as layer:
        bridge = EvidenceBridge(layer)
        bridge.start("round_safe", "source_quality", "What is the evidence?")
        assert len(bridge.pending()) == 1
        assert bridge.current("source_quality") is None
        assert bridge.finalize("round_safe")["execution_permission"] == "none"
        assert layer.reason(adapter_name="mock")["motion_command_generated"] is False
