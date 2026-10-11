"""Free-route request contract, redacted receipts, independent verifier."""
from __future__ import annotations

from io import BytesIO
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from bean.evaluation.openrouter_free_live import execute, normalise, ROUTE
from bean.evaluation.openrouter_free_verify import verify

PROJECT = Path(__file__).resolve().parents[2] / "experiments" / "autodev" / "seed_project"


class FakeResponse:
    def __init__(self, data):
        self.data = json.dumps(data).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return None

    def read(self, limit):
        return self.data[:limit]


def test_single_free_only_call_and_no_secret_in_receipt(tmp_path):
    calls = []
    def fake(req, timeout):
        calls.append(req)
        return FakeResponse({"model": "provider/test-model:free",
                             "choices": [{"message": {"content":
                                 "def clip_score(score):\n    return max(0, min(score, 100))\n"}}],
                             "usage": {"prompt_tokens": 39, "completion_tokens": 24}})
    result = execute(tmp_path, api_key="fixture-secret-never-log", request_fn=fake)
    assert len(calls) == 1
    payload = json.loads(calls[0].data)
    assert payload["model"] == ROUTE
    assert payload["max_tokens"] <= 1400
    assert result["provider_status"] == "proposal_generated"
    assert result["model_served"] == "provider/test-model:free"
    assert "fixture-secret-never-log" not in json.dumps(result)
    report = verify(artifact=tmp_path, project=PROJECT, output=tmp_path / "verification")
    assert report["verdict"] == "model_trial_passed"
    assert report["test_count"] == 7
    assert report["baseline_failed"] is True


def test_http402_reports_unavailable_and_no_paid_fallback(tmp_path):
    attempts = []
    def fake(req, timeout):
        attempts.append(req)
        raise HTTPError(req.full_url, 402, "Payment required", None, BytesIO(b"secret"))
    result = execute(tmp_path, api_key="fixture-secret", request_fn=fake)
    assert len(attempts) == 1
    assert result["reason"] == "OpenRouter HTTP 402"
    assert not (tmp_path / "proposal.py").exists()
    report = verify(artifact=tmp_path, project=PROJECT, output=tmp_path / "verification")
    assert report["verdict"] == "not_tested"
    assert report["provider_status"] == "provider_unavailable"


def test_bad_model_response_rejected_without_executing(tmp_path):
    def fake(req, timeout):
        return FakeResponse({"model": "some/free", "choices": [{"message": {"content": "hello"}}]})
    result = execute(tmp_path, api_key="fixture-secret", request_fn=fake)
    assert result["provider_status"] == "invalid_response"
    assert not (tmp_path / "proposal.py").exists()
    assert "fixture-secret" not in (tmp_path / "receipt.json").read_text()


def test_proposal_integrity_enforced(tmp_path):
    code = "def clip_score(score):\n    return max(0, min(score, 100))\n"
    (tmp_path / "proposal.py").write_text(code)
    (tmp_path / "receipt.json").write_text(json.dumps({
        "model_requested": "openrouter/free",
        "model_served": "fixture",
        "provider_status": "proposal_generated",
        "generated_source_sha256": hashlib.sha256(b"different").hexdigest()
    }))
    with pytest.raises(ValueError, match="hash mismatch"):
        verify(artifact=tmp_path, project=PROJECT, output=tmp_path / "verified")


def test_invalid_fences_and_empty_codes_rejected():
    for value in ("", "Hello, world!", (chr(96) * 3) + "python\nx=3\n"):
        with pytest.raises((ValueError, SyntaxError)):
            normalise(value)
