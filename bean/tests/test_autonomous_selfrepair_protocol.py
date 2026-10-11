"""Offline research protocol tests for BEAN's own model-authored self-repair.

No actual credentials, hosted models, or mutated production sources are used.
"""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

import pytest

from bean.evaluation import autonomous_selfrepair as lab

ORIGINAL = "def useful():\n    return 1\n"
EDIT = json.dumps({"edits": [{"find": "return 1", "replace": "return 2"}]})

class Reply:
    def __init__(self, code):
        self.code = code
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, *_):
        return json.dumps({
            "model": "example/verified-free-route",
            "choices": [{"message": {"content": self.code},
                         "finish_reason": "stop"}],
        }).encode()


def setup(tmp_path):
    root = tmp_path / "baseline"
    path = root / lab.TARGET
    path.parent.mkdir(parents=True)
    path.write_text(ORIGINAL, encoding="utf-8")
    return root


def test_model_authored_repair_is_proposal_not_self_execute(tmp_path):
    root = setup(tmp_path)
    requests = []
    def fake(req, timeout):
        requests.append(json.loads(req.data))
        return Reply(EDIT)
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        report = lab.generate(root=root, destination=tmp_path/"out",
                              key="fake-secret", request_fn=fake)
    assert report["status"] == "candidate_drafted_not_verified"
    assert len(report["attempts"]) == 1
    assert requests[0]["model"] == "openrouter/free"
    artifact = json.loads((tmp_path/"out"/"candidate.json").read_text())
    assert artifact["target"] == "bean/evaluation/bridge_peer_live_author.py"
    assert artifact["replacement"] == "def useful():\n    return 2\n"
    assert artifact["replacement_sha256"] == lab.sha(artifact["replacement"])
    assert (root / lab.TARGET).read_text() == ORIGINAL
    assert "fake-secret" not in json.dumps(report)


def test_two_bad_replies_then_own_model_fix_is_accepted(tmp_path):
    root = setup(tmp_path)
    answers = [Reply(None), Reply("not a patch"), Reply(EDIT)]
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        report = lab.generate(root=root, destination=tmp_path/"out",
                              key="fake", request_fn=lambda *_ , **kw: answers.pop(0))
    assert report["status"] == "candidate_drafted_not_verified"
    assert [x["status"] for x in report["attempts"]] == [
        "model_candidate_rejected", "model_candidate_rejected",
        "source_candidate_drafted"
    ]


def test_only_invalid_responses_are_rejected_and_preserved(tmp_path):
    root = setup(tmp_path)
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        report = lab.generate(root=root, destination=tmp_path/"out", key="fake",
                              request_fn=lambda *_ , **kw: Reply("no repair here"))
    assert report["status"] == "no_valid_candidate"
    assert len(report["attempts"]) == lab.MAX_CALLS
    assert not (tmp_path/"out"/"candidate.json").exists()
    assert (tmp_path/"out"/"author-receipt.json").exists()


def test_missing_key_does_not_create_any_candidate(tmp_path):
    root = setup(tmp_path)
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        report = lab.generate(root=root, destination=tmp_path/"out", key="")
    assert report["status"] == "provider_unavailable"
    assert report["attempts"][0]["rejection"] == "OPENROUTER_KEY_NOT_CONFIGURED"
    assert not (tmp_path/"out"/"candidate.json").exists()


def test_http402_is_reported_without_paid_retry(tmp_path):
    root = setup(tmp_path)
    calls = []
    def reject(req, timeout):
        calls.append(req)
        raise HTTPError(req.full_url, 402, "payment required", None, BytesIO(b"private"))
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        report = lab.generate(root=root, destination=tmp_path/"out", key="fake",
                              request_fn=reject)
    assert report["status"] == "provider_unavailable"
    assert len(calls) == 1
    assert "OPENROUTER_HTTP_402" in report["attempts"][0]["rejection"]


def test_source_commit_is_mandatory_and_author_cannot_touch_code(tmp_path):
    root = setup(tmp_path)
    with patch.object(lab, "current_commit", return_value="0"*40):
        report = lab.generate(root=root, destination=tmp_path/"out", key="fake",
                              request_fn=lambda *_ , **kw: Reply(EDIT))
    assert report["status"] == "source_integrity_failure"
    assert report["attempts"] == []
    assert (root/lab.TARGET).read_text() == ORIGINAL


def test_no_silent_source_change_on_bad_syntax(tmp_path):
    root = setup(tmp_path)
    bad_plan = json.dumps({"edits":[{"find":"return 1", "replace":"return ("}]})
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        report = lab.generate(root=root, destination=tmp_path/"out", key="fake",
                              request_fn=lambda *_ , **kw: Reply(bad_plan))
    assert report["status"] == "no_valid_candidate"
    assert (root/lab.TARGET).read_text() == ORIGINAL
    assert not (tmp_path/"out"/"candidate.json").exists()


def test_model_sees_failures_and_source_but_not_holdout_tests():
    called = []
    def fake(req, timeout):
        called.append(json.loads(req.data))
        return Reply(EDIT)
    content, meta = lab.model_request("fake", ORIGINAL, None, request_fn=fake)
    sent = called[0]["messages"][0]["content"]
    assert "empty or oversized edit plan" in sent
    assert "def useful():" in sent
    assert "test_failed_model_reply_causes_substantively_different_retry_strategy" not in sent
    assert "bean/tests/test_autonomous_selfrepair_oracle.py" not in sent
    assert meta["model_served"] == "example/verified-free-route"
