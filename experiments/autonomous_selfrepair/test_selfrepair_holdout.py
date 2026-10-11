"""Holdout for BEAN's model-authored self-repair.

The credential-bearing code author sees its old source and a sanitized
failure symptom, NEVER these acceptance tests. This file is not copied
into the author's prompt.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError
from io import BytesIO

import pytest

from bean.evaluation import bridge_peer_live_author as target


class Response:
    def __init__(self, content):
        self.content = content
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, *_):
        return json.dumps({
            "model": "synthetic/test-provider:free",
            "choices": [{"message": {"content": self.content},
                         "finish_reason": "stop"}],
        }).encode("utf-8")


def test_failed_model_reply_causes_substantively_different_retry_strategy():
    """Previously an invalid reply just appended 1 error sentence.

    Now demand an actual, information-preserving prompt-budget reduction,
    without specifying how the model-backed engineer must implement it.
    """
    calls = []
    source = ("from __future__ import annotations\n"
              + "\n".join("def unrelated_%d(): return %d" % (n, n) for n in range(140))
              + "\ndef call_model(key, original, **kwargs): return None\n"
              + "def author(root, *, key): return None\n")
    def backend(req, timeout):
        calls.append(json.loads(req.data))
        return Response(None)

    target.call_model("fictional-only", source, request_fn=backend)
    target.call_model("fictional-only", source, request_fn=backend,
                      feedback="empty or oversized edit plan")
    assert len(calls) == 2
    prompt1 = calls[0]["messages"][0]["content"]
    prompt2 = calls[1]["messages"][0]["content"]
    assert calls[0]["model"] == calls[1]["model"]
    assert calls[0]["model"] == "openrouter/free" or calls[0]["model"].endswith(":free")
    assert len(prompt1) > 3500
    assert len(prompt2) <= len(prompt1) * 0.80, (
        "The agent resent nearly identical context after its own model failed; "
        "retry needs a materially different, more focused strategy"
    )
    assert "def call_model(" in prompt2
    assert "def author(" in prompt2
    assert len(prompt2) >= 1000


def test_both_provider_replies_empty_never_fabricate_candidate():
    for response in (None, "", "\n"):
        content, metadata = target.call_model(
            "fictional-only", "def callable(): return 5", 
            request_fn=lambda req, timeout: Response(response))
        assert not content or not str(content).strip()
        with pytest.raises(ValueError):
            target.parse_plan(content)
        assert metadata["model_requested"] == "openrouter/free" or metadata["model_requested"].endswith(":free")


def test_source_changes_still_need_exact_unique_anchor_and_valid_syntax():
    original = "def one():\n    return 1\n\ndef two():\n    return 2\n"
    with pytest.raises(ValueError, match="ambiguous"):
        target.apply_edits(original, [{"find": "return", "replace": "yield"}])
    with pytest.raises(SyntaxError):
        target.apply_edits(original, [{
            "find": "return 1", "replace": "return ("
        }])


def test_no_paid_fallback_after_http402():
    calls = []
    def forbidden(req, timeout):
        calls.append(json.loads(req.data)["model"])
        raise HTTPError(req.full_url, 402, "paid route forbidden", None, BytesIO(b"secret"))
    with pytest.raises(RuntimeError, match="OPENROUTER_HTTP_402"):
        target.call_model("fictional-only", "def sample(): return 5",
                          request_fn=forbidden, feedback="provider unavailable")
    assert len(calls) == 1
    assert calls[0] == "openrouter/free" or calls[0].endswith(":free")


def test_parser_rejects_unknown_code_mutation_commands():
    for response in (
        '{"edits":[{"find":"x=1","replace":"x=2"}],"system_command":"rm -rf /"}',
        '{"edits":[{"find":"x=1","replace":"x=2"}],"files":["tests"]}',
        '{"edits":[]}',
    ):
        with pytest.raises(ValueError):
            target.parse_plan(response)
