"""Bridge peer feedback revision protocol: no network or real model needed."""
import json
from pathlib import Path
from unittest.mock import patch

from bean.evaluation import bridge_peer_live_author as base
from bean.evaluation import bridge_feedback_revision as revision

ORIGINAL = "from datetime import datetime\n\ndef calc(value):\n    return value\n"
FIRST = "from datetime import datetime, timezone\n\ndef calc(value):\n    return value\n"
SECOND = "from datetime import datetime, timezone\n\ndef calc(value):\n    return max(0, value)\n"

def fixture(tmp_path):
    bridge, challenge = tmp_path/"bridge", tmp_path/"challenge"
    prior, failed, output = tmp_path/"prior", tmp_path/"failed", tmp_path/"out"
    for root, part in [(bridge, base.TARGET), (challenge, base.ORACLE)]:
        (root / part).parent.mkdir(parents=True)
    (bridge/base.TARGET).write_text(ORIGINAL)
    (challenge/base.ORACLE).write_text("sealed oracle test data")
    prior.mkdir()
    failed.mkdir()
    candidate = {
        "schema": "bean.novel-repair.v1",
        "base_commit": base.BRIDGE_SHA,
        "challenge_commit": base.CHALLENGE_SHA,
        "path": str(base.TARGET),
        "source_sha256": base.sha(ORIGINAL),
        "oracle_sha256": base.sha("sealed oracle test data"),
        "replacement_sha256": base.sha(FIRST),
        "changed_lines": 2,
        "model": base.ROUTE, "provider": "openrouter",
        "replacement": FIRST,
    }
    base.save(prior/"candidate.json", candidate)
    base.save(prior/"author-receipt.json", {
        "status": "candidate_drafted_not_tested",
        "candidate_sha256": base.sha((prior/"candidate.json").read_bytes()),
        "replacement_sha256": base.sha(FIRST),
    })
    base.save(failed/"verify-receipt.json", {
        "schema": "bean.novel-repair.receipt.v1",
        "phase": "verify", "result": "rejected", "suite_passed": False,
        "diff": {"replacement_sha256": base.sha(FIRST)},
        "baseline": {"normal_passed": True, "oracle_red": True},
        "test_tail": "FAILED (failures=2)\n"
                     "test_same_instant_never_changes_observed_rma_into_asserted_zero\n"
                     "test_same_instant_keeps_production_window_stable",
    })
    return bridge, challenge, prior, failed, output

def head_mock(root, bridge):
    return base.BRIDGE_SHA if root == bridge else base.CHALLENGE_SHA

def test_feedback_revises_previous_model_source_and_preserves_chained_evidence(tmp_path):
    bridge, challenge, prior, failed, output = fixture(tmp_path)
    calls = []
    def mock(key, source, *, feedback, model, request_fn):
        calls.append((source, feedback, model))
        return json.dumps({"edits": [{"find": "return value",
                                       "replace": "return max(0, value)"}]}), {
            "model_requested": model, "model_served": model, "finish_reason": "stop"
        }
    with (patch.object(base, "head", side_effect=lambda x: head_mock(x, bridge)),
          patch.object(base, "call_model", side_effect=mock)):
        result = revision.revision(
            bridge=bridge, challenge=challenge, previous=prior, verification=failed,
            out=output, key="fake-credential"
        )
    assert result["status"] == "revised_candidate_not_tested"
    assert result["attempted_requests"] == 1
    assert len(calls) == 1
    assert calls[0][0] == FIRST
    assert "rma" in calls[0][1].lower()
    assert "production" in calls[0][1].lower()
    saved = json.loads((output/"candidate.json").read_text())
    assert saved["source_sha256"] == base.sha(ORIGINAL)
    assert saved["replacement"] == SECOND
    assert saved["replacement_sha256"] == base.sha(SECOND)
    assert (bridge/base.TARGET).read_text() == ORIGINAL
    assert result["verifier_receipt_sha256"] == base.sha((failed/"verify-receipt.json").read_bytes())
    assert "fake-credential" not in json.dumps(result)

def test_fake_success_report_is_not_used_as_learning_feedback(tmp_path):
    bridge, challenge, prior, failed, output = fixture(tmp_path)
    path = failed/"verify-receipt.json"
    record = json.loads(path.read_text())
    record["result"] = "validated_change"
    base.save(path, record)
    with patch.object(base, "head", side_effect=lambda x: head_mock(x, bridge)):
        result = revision.revision(bridge=bridge, challenge=challenge,
                                   previous=prior, verification=failed,
                                   out=output, key="fake")
    assert result["status"] == "invalid_prior_evidence"
    assert not (output/"candidate.json").exists()

def test_tampered_previous_code_is_refused_before_model_request(tmp_path):
    bridge, challenge, prior, failed, output = fixture(tmp_path)
    cand = prior/"candidate.json"
    d = json.loads(cand.read_text())
    d["replacement"] = SECOND
    base.save(cand, d)
    with (patch.object(base, "head", side_effect=lambda x: head_mock(x, bridge)),
          patch.object(base, "call_model") as unauthorized):
        result = revision.revision(bridge=bridge, challenge=challenge,
                                   previous=prior, verification=failed,
                                   out=output, key="fake")
    assert result["status"] == "invalid_prior_evidence"
    unauthorized.assert_not_called()

def test_missing_secret_cannot_create_a_fake_revision(tmp_path):
    bridge, challenge, prior, failed, output = fixture(tmp_path)
    with patch.object(base, "head", side_effect=lambda x: head_mock(x, bridge)):
        result = revision.revision(bridge=bridge, challenge=challenge,
                                   previous=prior, verification=failed,
                                   out=output, key="")
    assert result["status"] == "provider_unavailable"
    assert result["attempted_requests"] == 1
    assert not (output/"candidate.json").exists()

def test_feedback_does_not_expose_unbounded_tracebacks_or_oracle_source():
    original = "FAILED (failures=5)\n" + "x"*5000 + "\ntest_same_instant_rma_error"
    summary = revision.feedback_summary({"test_tail": original})
    assert len(summary) <= 900
    assert "x"*100 not in summary
    assert "test_same_instant_rma_error" in summary
