"""Lab021 reproducible oracle, leak boundaries, and model-repair tests."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import pytest
from bean.evaluation.transfer_tasks import TASKS
from bean.evaluation.transfer_author import normalize, generate, ROUTE
from bean.evaluation.transfer_oracle import (
    validate_source, fixtures, subprocess_grade, grade,
)

GOLD = {
    "intervals": """def merge_time_windows(windows):
    intervals = []
    for start, end in windows:
        if end < start:
            raise ValueError('range')
        if end > start:
            intervals.append((start, end))
    intervals.sort()
    merged = []
    for start, end in intervals:
        if merged and merged[-1][1] >= start:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
""",
    "dependencies": """def resolve_dependency_order(graph):
    nodes = set(graph)
    for deps in graph.values():
        nodes.update(deps)
    unresolved = {n: set(graph.get(n, [])) for n in nodes}
    order = []
    while unresolved:
        ready = sorted(n for n, deps in unresolved.items() if not deps)
        if not ready:
            raise ValueError('cycle')
        n = ready[0]
        order.append(n)
        del unresolved[n]
        for deps in unresolved.values():
            deps.discard(n)
    return order
""",
    "inventory": """def summarize_inventory_movements(rows):
    seen = set()
    totals = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('row')
        event_id = row.get('event_id')
        sku = row.get('sku')
        delta = row.get('delta')
        if not isinstance(event_id, str) or not event_id:
            raise ValueError('id')
        if not isinstance(sku, str) or not sku:
            raise ValueError('sku')
        if type(delta) is not int:
            raise ValueError('delta')
        if event_id in seen:
            continue
        seen.add(event_id)
        totals[sku] = totals.get(sku, 0) + delta
    return {sku: totals[sku] for sku in sorted(totals)}
""",
}


def test_unrelated_domain_baselines_are_genuinely_broken(tmp_path):
    for task in TASKS:
        p = tmp_path / (task.task_id + ".py")
        p.write_text(task.original)
        result = subprocess_grade(task.task_id, p, "development")
        assert result["passed"] < result["total"], task.task_id


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.task_id)
def test_independent_holdout_accepts_complete_solution(task, tmp_path):
    p = tmp_path / "solution.py"
    p.write_text(GOLD[task.task_id])
    validate_source(GOLD[task.task_id], task.function)
    for phase in ("development", "holdout"):
        grade_result = subprocess_grade(task.task_id, p, phase)
        assert grade_result["passed"] == grade_result["total"], (task.task_id, phase, grade_result)


def test_hidden_test_split_is_deterministically_distinct():
    for task in TASKS:
        assert fixtures(task.task_id, "holdout") != fixtures(task.task_id, "development")


@pytest.mark.parametrize("source", [
    "import os\ndef merge_time_windows(windows): return []",
    "def merge_time_windows(windows):\n    return open('/etc/passwd').read()",
    "def merge_time_windows(windows):\n    return (1).__class__",
    "def merge_time_windows(windows):\n    return globals()",
    "x = 4\ndef merge_time_windows(windows): return []",
])
def test_untrusted_python_rejected(source):
    with pytest.raises(ValueError):
        validate_source(source, "merge_time_windows")


def test_code_fences_and_ambiguous_responses():
    raw = "```python\ndef merge_time_windows(windows):\n    return []\n```"
    assert normalize(raw, "merge_time_windows") == "def merge_time_windows(windows):\n    return []\n"
    with pytest.raises(ValueError):
        normalize("No code returned", "merge_time_windows")
    with pytest.raises(ValueError):
        normalize(raw + "\n" + raw, "merge_time_windows")


class FixtureResponse:
    def __init__(self, model, source):
        self.payload = json.dumps({
            "model": model,
            "choices": [{"message": {"content": source}}],
        }).encode()
    def __enter__(self):
        return self
    def __exit__(self, *ignored):
        return None
    def read(self, limit):
        return self.payload[:limit]


def test_secret_never_enters_receipt_and_routing_is_free(tmp_path):
    requests = []
    def fake(request, timeout):
        requests.append(request)
        prompt = json.loads(request.data)["messages"][0]["content"]
        assert json.loads(request.data)["model"] == ROUTE
        assert "fixture-secret" not in prompt
        task = next(x for x in TASKS if "Objective ID: " + x.task_id in prompt)
        return FixtureResponse("provider/fixture:free", GOLD[task.task_id])
    out = tmp_path / "first"
    receipt = generate(out, api_key="fixture-secret-never-log", request_fn=fake)
    assert receipt["total_requests"] == len(TASKS)
    assert all(x["provider_status"] == "proposal_generated" for x in receipt["tasks"])
    assert "fixture-secret-never-log" not in (out / "receipt.json").read_text()
    report = grade(out, tmp_path / "dev-feedback.json", phase="development")
    assert report["initial_total"] == report["possible_total"]
    revision = generate(tmp_path / "second", api_key="fixture-secret-never-log",
                        feedback_file=tmp_path / "dev-feedback.json", request_fn=fake)
    assert revision["total_requests"] == 0
    assert all(r["provider_status"] == "already_passed" for r in revision["tasks"])
    assert len(requests) == len(TASKS)


def test_grading_rejects_corrupted_source_hash(tmp_path):
    output = tmp_path / "raw"
    output.mkdir()
    src = GOLD["intervals"]
    (output / "intervals.py").write_text(src)
    doc = {
        "schema": "bean.autonomy.lab021.generation.v1",
        "total_requests": 1,
        "tasks": [
            {"task_id": "intervals", "provider_status": "proposal_generated",
             "model_requested": ROUTE, "source_sha256": hashlib.sha256(b"fake").hexdigest()},
        ],
    }
    (output / "receipt.json").write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="digest"):
        grade(output, tmp_path / "out.json", phase="holdout")


def test_no_secret_provider_yields_unavailable_not_fake_success(tmp_path):
    output = tmp_path / "missing"
    receipt = generate(output, api_key="")
    assert receipt["total_requests"] == 0
    assert all(x["provider_status"] == "unavailable" for x in receipt["tasks"])
    result = grade(output, tmp_path / "feedback.json", phase="development")
    assert result["initial_total"] == 0
