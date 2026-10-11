"""Lab020 protocol tests; no provider requests or keys needed."""
import hashlib
import json
from pathlib import Path

import pytest

from experiments.llm_growth_lab020.lab020 import (
    ROUTE, ast_baseline, checked_history, digest, generate, normalise,
    score_candidate, validate, TARGET,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / TARGET
TESTS = ROOT / "experiments/llm_growth_lab020/test_selection_identity.py"


class Response:
    def __init__(self, data):
        self.data = json.dumps(data).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return None
    def read(self, limit):
        return self.data[:limit]


def fake_with(source, calls):
    def request(req, timeout):
        body = json.loads(req.data)
        calls.append(body)
        return Response({"model": "fixture/free", "choices": [{
            "message": {"content": source}, "finish_reason": "stop"}]})
    return request


def patched(source):
    needle = "candidate.identifier for candidate in opportunities"
    assert needle in source
    return source.replace(
        needle, "candidate.identifier.strip().casefold() for candidate in opportunities")


def test_real_core_baseline_is_demonstrably_broken():
    baseline = score_candidate(SOURCE.read_text(encoding="utf-8"), test_source=TESTS)
    assert not baseline["passed"]
    assert baseline["total"] == 14
    assert baseline["passed_tests"] <= 11


def test_revised_full_source_passes_core_reproduction_and_sealed_holdout():
    fixed = patched(SOURCE.read_text(encoding="utf-8"))
    assert score_candidate(fixed, test_source=TESTS)["passed"]
    held = ROOT / "experiments/llm_growth_lab020/test_selection_holdout.py"
    assert score_candidate(fixed, test_source=held)["passed"]


def test_iterative_feedback_is_persistent_and_inference_is_free_only(tmp_path):
    source = SOURCE.read_text(encoding="utf-8")
    calls = []
    first = tmp_path / "gen0"
    receipt = generate(source_path=SOURCE, prior_history=None, iteration=0,
                       out=first, key="test-key-will-not-appear",
                       request_fn=fake_with(source, calls))
    assert receipt["requested"] == ROUTE
    assert receipt["requested_count"] == 1
    outcome0 = validate(source_path=SOURCE, test_source=TESTS, proposal_dir=first,
                        prior_history=None, iteration=0, out=tmp_path / "val0")
    assert outcome0["outcome"] == "rejected"
    assert outcome0["test"]["passed_tests"] < 14
    second = tmp_path / "gen1"
    receipt1 = generate(source_path=SOURCE,
                        prior_history=tmp_path / "val0/history.json", iteration=1,
                        out=second, key="test-key-will-not-appear",
                        request_fn=fake_with(patched(source), calls))
    outcome1 = validate(source_path=SOURCE, test_source=TESTS, proposal_dir=second,
                        prior_history=tmp_path / "val0/history.json",
                        iteration=1, out=tmp_path / "val1")
    assert outcome1["outcome"] == "validated"
    saved = checked_history(tmp_path / "val1/history.json")
    assert len(saved["entries"]) == 2
    assert saved["entries"][0]["outcome"] == "rejected"
    assert saved["entries"][1]["outcome"] == "validated"
    assert [entry["iteration"] for entry in saved["entries"]] == [0, 1]
    assert all(call["model"] == "openrouter/free" for call in calls)
    assert all(call["max_tokens"] <= 3000 for call in calls)
    assert all("test_selection_identity" not in str(call) for call in calls)
    for item in [first, second, tmp_path / "val0", tmp_path / "val1"]:
        assert "test-key-will-not-appear" not in "".join(
            file.read_text(encoding="utf-8") for file in item.glob("*.json"))


def test_history_mutation_rejected(tmp_path):
    source = SOURCE.read_text(encoding="utf-8")
    first = tmp_path / "gen"
    generate(source_path=SOURCE, prior_history=None, iteration=0, out=first,
             key="fixture", request_fn=fake_with(source, []))
    validate(source_path=SOURCE, test_source=TESTS, proposal_dir=first,
             prior_history=None, iteration=0, out=tmp_path / "val")
    path = tmp_path / "val/history.json"
    data = json.loads(path.read_text())
    data["entries"][0]["passed"] = 99
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="integrity"):
        checked_history(path)


def test_source_hash_tamper_fails_before_running_candidate(tmp_path):
    src = SOURCE.read_text()
    gen = tmp_path / "gen"
    generate(source_path=SOURCE, prior_history=None, iteration=0, out=gen,
             key="fixture", request_fn=fake_with(patched(src), []))
    (gen / "proposal.py").write_text(src, encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint"):
        validate(source_path=SOURCE, test_source=TESTS, proposal_dir=gen,
                 prior_history=None, iteration=0, out=tmp_path / "val")


def test_ast_has_no_casefold_operator_in_first_three_trials(tmp_path):
    report = ast_baseline(source_path=SOURCE, test_source=TESTS,
                          out=tmp_path / "ast", max_attempts=3)
    assert report["attempts"] == 3
    assert not report["success"]
    assert len(report["results"]) == 3


def test_normalizer_requires_actual_rank_function():
    with pytest.raises(ValueError, match="rank_improvements"):
        normalise("def unrelated(): return 1")
