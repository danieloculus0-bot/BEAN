"""Ollama path tests use an explicit fake API, never claim LLM intelligence."""
from __future__ import annotations

import json

import pytest

from bean.evaluation.lab023_ollama import (
    Ollama, OllamaUnavailable, development_stage, training_stage,
)
from bean.evaluation.transfer_tasks import TASKS
from bean.evaluation.transfer_oracle import grade
from bean.evaluation.lifelong_transfer_lab023 import learn, transfer, judge
from experiments.agent_arena.cases import CASES


class Response:
    def __init__(self, body):
        self.body = json.dumps(body).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, n):
        return self.body[:n]


class FakeOllamaTransport:
    """A fake model is only for checking the API transport and file contracts."""
    def __init__(self, model="qwen2.5-coder:0.5b"):
        self.model = model
        self.calls = []
    def __call__(self, request, timeout=1):
        self.calls.append(request)
        if request.full_url.endswith("/api/tags"):
            return Response({"models": [{"name": self.model}]})
        assert request.full_url.endswith("/api/generate")
        p = json.loads(request.data)
        assert p["model"] == self.model
        assert p["stream"] is False
        prompt = p["prompt"]
        if "general coding" in prompt or "research reflection engine" in prompt:
            response = "Verify ordering, edge cases, and input integrity."
        elif "merge_time_windows" in prompt:
            response = "def merge_time_windows(windows):\n    return []\n"
        elif "resolve_dependency_order" in prompt:
            response = "def resolve_dependency_order(graph):\n    return []\n"
        elif "summarize_inventory_movements" in prompt:
            response = "def summarize_inventory_movements(rows):\n    return {}\n"
        else:
            response = ""
        return Response({"done": True, "response": response})


def test_ollama_writes_real_hashed_training_receipts_without_network(tmp_path):
    transport = FakeOllamaTransport()
    model = Ollama(model=transport.model, transport=transport)
    status = model.preflight()
    assert status["ready"] and status["route"] == "ollama/qwen2.5-coder:0.5b"
    receipts = training_stage(model, tmp_path)
    assert len(receipts["tasks"]) == len(TASKS)
    assert all(x["provider_status"] == "proposal_generated" for x in receipts["tasks"])
    assert all(x["model_requested"] == model.route for x in receipts["tasks"])
    report = development_stage(tmp_path)
    assert report["phase"] == "development"
    assert report["possible_total"] >= 150
    result = learn(tmp_path / "training", tmp_path / "development.json",
                   tmp_path / "state.sqlite", tmp_path / "learning.json",
                   api_key="local-no-secret", reflector=model.reflect)
    assert result["restart_verified"]
    assert result["model_authored_lessons"] == 3
    assert len(transport.calls) == 8  # two preflights, three training, three reflections


def test_full_module_author_records_genuine_candidate_not_fixture_success():
    transport = FakeOllamaTransport()
    model = Ollama(model=transport.model, transport=transport)
    spec = {
        "source": "def merge_time_windows(windows):\n    return windows\n",
        "prompt": "Repair merge_time_windows for all edge cases.",
    }
    receipt, source = model.author(spec, "ignored")
    assert receipt["model_requested"] == model.route
    assert receipt["status"] == "candidate_drafted_not_tested"
    assert source.startswith("def merge_time_windows")
    assert source != spec["source"]


def test_no_connection_and_missing_model_fail_closed():
    with pytest.raises(ValueError, match="loopback-only"):
        Ollama(host="http://example.com:11434")
    with pytest.raises(ValueError):
        Ollama(model="../../credentials")
    absent = Ollama(model="qwen2.5-coder:3b",
                    transport=FakeOllamaTransport("qwen2.5-coder:0.5b"))
    with pytest.raises(OllamaUnavailable, match="not downloaded"):
        absent.preflight()


def test_incomplete_local_response_rejected():
    client = Ollama(model="qwen2.5-coder:0.5b",
                    transport=lambda req, timeout=1: Response(
                        {"done": False, "response": "unfinished"}))
    with pytest.raises(OllamaUnavailable, match="incomplete"):
        client.complete("hello")


def test_ollama_training_is_valid_under_independent_grade(tmp_path):
    fake = FakeOllamaTransport()
    provider = Ollama(model=fake.model, transport=fake)
    provider.training(tmp_path)
    result = grade(tmp_path, tmp_path / "score.json", phase="development")
    assert result["phase"] == "development"
    assert result["baseline_total"] > 0
    # Broken generated code does NOT win; passing source receipt alone is insufficient.
    assert result["selected_total"] < result["possible_total"]
