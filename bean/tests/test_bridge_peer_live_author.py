"""Blind Core-to-Bridge author tests. No real provider, credentials or ERP data."""
from __future__ import annotations
from io import BytesIO
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from urllib.error import HTTPError

import pytest
from bean.evaluation import bridge_peer_live_author as author

OLD = "from datetime import datetime\n\ndef f(value):\n    return value\n"
NEW = "from datetime import datetime, timezone\n\ndef f(value):\n    return value\n"

class Reply:
    def __init__(self, content):
        self.content = content
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, *_):
        return json.dumps({
            "model": "provider/real-free-model",
            "choices": [{"message": {"content": self.content},
                         "finish_reason": "stop"}]
        }).encode()

def setup(tmp_path):
    bridge, challenge = tmp_path / "bridge", tmp_path / "challenge"
    (bridge / author.TARGET.parent).mkdir(parents=True)
    (challenge / author.ORACLE.parent).mkdir(parents=True)
    (bridge / author.TARGET).write_text(OLD, encoding="utf-8")
    (challenge / author.ORACLE).write_text("sealed opaque acceptance tests", encoding="utf-8")
    return bridge, challenge

def plan(edits):
    return json.dumps({"edits": edits})

def test_valid_model_edit_is_source_authored_not_preprogrammed(tmp_path):
    bridge, challenge = setup(tmp_path)
    edit = plan([{"find": "from datetime import datetime",
                  "replace": "from datetime import datetime, timezone"}])
    requests = []
    def fake(req, timeout):
        requests.append(req)
        return Reply(edit)
    with patch.object(author, "head", side_effect=lambda root:
                      author.BRIDGE_SHA if root == bridge else author.CHALLENGE_SHA):
        result = author.author(bridge=bridge, challenge=challenge,
                               out=tmp_path / "proposal", key="fictional-secret", request_fn=fake)
    assert result["status"] == "candidate_drafted_not_tested"
    assert result["attempted_requests"] == 1
    saved = json.loads((tmp_path / "proposal" / "candidate.json").read_text())
    assert saved["replacement"] == NEW
    assert saved["provider"] == "openrouter"
    assert saved["replacement_sha256"] == author.sha(NEW)
    assert (bridge / author.TARGET).read_text() == OLD
    assert len(requests) == 1
    assert json.loads(requests[0].data)["model"] == "openrouter/free"
    assert "fictional-secret" not in json.dumps(result)
    assert "fictional-secret" not in (tmp_path / "proposal" / "author-receipt.json").read_text()

def test_one_bad_plan_is_retried_without_fixed_fallback(tmp_path):
    bridge, challenge = setup(tmp_path)
    attempts = [Reply("This is not a code patch"), Reply(plan([
        {"find": "return value", "replace": "return max(0, value)"}
    ]))]
    with patch.object(author, "head", side_effect=[
        author.BRIDGE_SHA, author.CHALLENGE_SHA,
    ]):
        report = author.author(bridge=bridge, challenge=challenge, out=tmp_path/"out",
                               key="test", request_fn=lambda *_ , **kw: attempts.pop(0))
    assert report["status"] == "candidate_drafted_not_tested"
    assert report["attempted_requests"] == 2
    assert "return max(0, value)" in json.loads((tmp_path/"out"/"candidate.json").read_text())["replacement"]

def test_two_invalid_model_attempts_do_not_produce_verified_source(tmp_path):
    bridge, challenge = setup(tmp_path)
    with patch.object(author, "head", side_effect=[author.BRIDGE_SHA, author.CHALLENGE_SHA]):
        report = author.author(bridge=bridge, challenge=challenge, out=tmp_path/"out",
                               key="test", request_fn=lambda *_ , **kw: Reply("no source"))
    assert report["status"] == "invalid_model_edit_plan"
    assert report["attempted_requests"] == 2
    assert not (tmp_path/"out"/"candidate.json").exists()

def test_no_key_does_not_invent_generated_code(tmp_path):
    bridge, challenge = setup(tmp_path)
    with patch.object(author, "head", side_effect=[author.BRIDGE_SHA, author.CHALLENGE_SHA]):
        report = author.author(bridge=bridge, challenge=challenge, out=tmp_path/"out",
                               key="")
    assert report["status"] == "provider_unavailable"
    assert report["reason"] == "OPENROUTER_KEY_NOT_CONFIGURED"
    assert not (tmp_path/"out"/"candidate.json").exists()

def test_fails_if_bridge_or_oracle_sha_changes(tmp_path):
    bridge, challenge = setup(tmp_path)
    with patch.object(author, "head", return_value="f"*40):
        report = author.author(bridge=bridge, challenge=challenge, out=tmp_path/"out",
                               key="test")
    assert report["status"] == "input_integrity_failure"
    assert report["attempted_requests"] == 0

def test_ambiguous_replace_anchor_is_rejected():
    with pytest.raises(ValueError, match="ambiguous"):
        author.apply_edits("x=1\nx=1\n", [{"find": "x=1", "replace": "x=2"}])

def test_syntax_broken_or_unbounded_candidate_is_rejected():
    with pytest.raises(SyntaxError):
        author.apply_edits("x=1\n", [{"find": "x=1", "replace": "def broken("}])
    with pytest.raises(ValueError, match="100 lines"):
        author.apply_edits("x=1\n", [{
            "find": "x=1", "replace": "\n".join("a%d = %d" % (i,i) for i in range(110))
        }])

def test_plan_fence_and_unexpected_fields():
    fence = chr(96)*3
    assert author.parse_plan(fence + "json\n" + plan([
        {"find": "x=1", "replace": "x=2"}
    ]) + "\n" + fence)[0]["replace"] == "x=2"
    for value in ("", "{}", "[]", '{"edits":[]}', '{"edits":{},"commands":["ls"]}'):
        with pytest.raises(ValueError):
            author.parse_plan(value)

def test_http402_never_triggers_paid_fallback(tmp_path):
    bridge, challenge = setup(tmp_path)
    calls = []
    def rejected(req, timeout):
        calls.append(req)
        raise HTTPError(req.full_url, 402, "payment required", None, BytesIO(b"private"))
    with patch.object(author, "head", side_effect=[author.BRIDGE_SHA, author.CHALLENGE_SHA]):
        report = author.author(bridge=bridge, challenge=challenge, out=tmp_path/"out",
                               key="secret", request_fn=rejected)
    assert report["status"] == "provider_unavailable"
    assert report["attempted_requests"] == 1
    assert report["reason"] == "OPENROUTER_HTTP_402"
    assert len(calls) == 1
    assert "private" not in (tmp_path/"out"/"author-receipt.json").read_text()


def test_free_model_prose_wrapper_is_not_mistaken_for_a_bad_edit_plan():
    content = (
        "I found a likely change.\n"
        + json.dumps({"edits":[{"find":"x=1", "replace":"x=2"}]})
        + "\nPlease test it independently."
    )
    assert author.parse_plan(content) == [{"find": "x=1", "replace": "x=2"}]


def test_invalid_edit_receipt_explains_failure_without_copying_raw_model_text(tmp_path):
    bridge, challenge = setup(tmp_path)
    with patch.object(author, "head", side_effect=[author.BRIDGE_SHA, author.CHALLENGE_SHA]):
        report = author.author(bridge=bridge, challenge=challenge, out=tmp_path/"out",
                               key="nonloggable-secret",
                               request_fn=lambda *_ , **kw: Reply("nonsensical provider text"))
    assert report["status"] == "invalid_model_edit_plan"
    assert report["rejected_stage"] == "model response has no usable JSON edits"
    assert report["attempted_requests"] == 2
    assert "nonloggable-secret" not in json.dumps(report)
    assert "nonsensical provider text" not in json.dumps(report)
