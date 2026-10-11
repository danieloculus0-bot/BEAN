"""Test scheduled evidence review against BEAN's actual durable task ledger."""
from datetime import datetime, timezone
from bean.integration.reasoning_layer import BeanReasoningLayer
from bean.integration.evidence_bridge import EvidenceBridge, SourceClaim
from bean.integration.evidence_review import EvidenceReviewAction, ReviewBatch
from bean.runtime.task_engine import TaskEngine, TaskSpec

T = "2026-10-10T21:00:00Z"


def source(identifier, run, origin, value):
    return SourceClaim(identifier, run, origin, f"fixture:{identifier}", value,
                       True, f"check:{identifier}", T)


def test_durable_autonomous_evidence_cycle_adapts_across_restart(tmp_path):
    path = str(tmp_path / "scheduled_core.sqlite")
    now = [datetime(2026, 10, 10, 21, tzinfo=timezone.utc).timestamp()]
    incoming = []
    def inbox():
        return incoming.pop(0) if incoming else None
    spec = TaskSpec("evidence_review", "read_host_evidence", interval_seconds=60, max_attempts=2)
    with BeanReasoningLayer(path) as layer:
        bridge = EvidenceBridge(layer)
        engine = TaskEngine({"read_host_evidence": EvidenceReviewAction(bridge, inbox)},
                            utc_timestamp=lambda: now[0])
        engine.configure([spec])
        assert engine.poll_due()[0]["status"] == "n/a"
        now[0] += 60
        incoming.append(ReviewBatch("round_first", "calibration_state", "Is it valid?", (
            source("lab_a", "round_first", "lab_a", "valid"),
            source("lab_b", "round_first", "lab_b", "valid"),
        )))
        assert engine.poll_due()[0]["status"] == "success"
        assert bridge.current("calibration_state")["value"] == "valid"
        assert len(engine.history("evidence_review")) == 2
    with BeanReasoningLayer(path) as layer:
        bridge = EvidenceBridge(layer)
        engine = TaskEngine({"read_host_evidence": EvidenceReviewAction(bridge, inbox)},
                            utc_timestamp=lambda: now[0])
        assert engine.recover_interrupted() == 0
        assert bridge.current("calibration_state")["value"] == "valid"
        now[0] += 60
        incoming.append(ReviewBatch("round_changed", "calibration_state", "Has it changed?", (
            source("lab_c", "round_changed", "lab_c", "invalid"),
            source("lab_d", "round_changed", "lab_d", "invalid"),
        )))
        assert engine.poll_due()[0]["status"] == "success"
        assert bridge.current("calibration_state")["value"] == "invalid"
        now[0] += 60
        incoming.append(ReviewBatch("round_conflict", "calibration_state", "Any conflict?", (
            source("lab_e", "round_conflict", "lab_e", "invalid"),
            source("lab_f", "round_conflict", "lab_f", "valid"),
        )))
        assert engine.poll_due()[0]["status"] == "n/a"
        assert bridge.current("calibration_state") is None
        assert len(engine.history("evidence_review")) == 4
        assert all(x["state"] in {"success", "n/a"} for x in engine.history("evidence_review"))
        assert engine.snapshot()[0]["state"] == "ready"


def test_scheduler_requires_review_after_interrupted_attempt(tmp_path):
    path = str(tmp_path / "interrupted.sqlite")
    now = [datetime(2026, 10, 10, 21, tzinfo=timezone.utc).timestamp()]
    with BeanReasoningLayer(path) as layer:
        bridge = EvidenceBridge(layer)
        engine = TaskEngine({"read_host_evidence": EvidenceReviewAction(bridge, lambda: None)},
                            utc_timestamp=lambda: now[0])
        engine.configure([TaskSpec("evidence_review", "read_host_evidence", 60)])
        assert engine._claim()["task_id"] == "evidence_review"
    with BeanReasoningLayer(path) as layer:
        bridge = EvidenceBridge(layer)
        engine = TaskEngine({"read_host_evidence": EvidenceReviewAction(bridge, lambda: None)},
                            utc_timestamp=lambda: now[0])
        assert engine.recover_interrupted() == 1
        now[0] += 1000
        assert engine.poll_due() == []
        assert engine.snapshot()[0]["state"] == "needs_review"
        assert engine.history("evidence_review")[0]["state"] == "unknown"


def test_invalid_host_batch_never_triggers_model_update(tmp_path):
    with BeanReasoningLayer(str(tmp_path / "invalid.sqlite")) as layer:
        bridge = EvidenceBridge(layer)
        inbox = lambda: {"fake_claim": True}
        engine = TaskEngine({"read_host_evidence": EvidenceReviewAction(bridge, inbox)},
                            utc_timestamp=lambda: 1791666000)
        engine.configure([TaskSpec("evidence_review", "read_host_evidence", 60)])
        assert engine.poll_due()[0]["status"] == "failed"
        assert bridge.current("calibration_state") is None
