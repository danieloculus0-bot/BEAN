"""Synthetic mechanism tests; not proof of autonomous creativity."""
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from bean.creativity.sketch_lab import SketchLab, OllamaSketchProvider, draw_svg, validate_shapes
from bean.learning import NativeReasoningService


class FakeModel:
    model_id = "synthetic-fixture-sketch"
    provider_kind = "synthetic_fixture"

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def complete(self, query, context):
        self.requests.append(query)
        return self.replies.pop(0)


def plan(subject="a bicycle"):
    return '{"subject":"' + subject + '","reference_query":"bicycle outline line drawing"}'


def drawing():
    return ('{"description":"A bicycle with two wheels and a frame",'
            '"shapes":[{"type":"circle","cx":70,"cy":170,"r":40},'
            '{"type":"circle","cx":185,"cy":170,"r":40},'
            '{"type":"line","x1":70,"y1":170,"x2":130,"y2":110}]}') 


def review():
    return '{"claimed_subject":"bicycle","changes":"add handlebars","satisfied":false}'


def test_core_owned_sketch_retains_hash_and_reports_unverified(tmp_path):
    model = FakeModel([plan(), drawing(), review(), drawing(), review()])
    core = NativeReasoningService(tmp_path / "lessons.sqlite3", model=model)
    try:
        outcome = SketchLab(core).run(
            task_ref="fixture-bicycle", output_dir=tmp_path / "out",
            backend="stdlib", max_attempts=2)
        assert outcome["subject_chosen_by_BEAN_model"] == "a bicycle"
        assert outcome["attempts"] == 2
        assert outcome["final_status"] == "unverified"
        assert outcome["visual_success_independently_verified"] is False
        assert len([e for e in core.bank.journal.events()
                    if e["kind"] == "trial" and
                    e["data"].get("experiment") == "bean_sketch_v1"]) == 2
        for row in outcome["history"]:
            assert row["sha256"] and Path(row["svg"]).exists()
            assert ET.parse(row["svg"]).getroot().tag.endswith("svg")
    finally:
        core.close()


def test_model_chooses_subject_no_fixed_catalog(tmp_path):
    model = FakeModel([plan("an imaginary flying machine"), drawing(), review()])
    core = NativeReasoningService(tmp_path / "core.db", model=model)
    try:
        result = SketchLab(core).run(
            task_ref="anything", output_dir=tmp_path, max_attempts=1,
            backend="stdlib")
        assert result["subject_chosen_by_BEAN_model"] == "an imaginary flying machine"
        assert "Choose ANY subject" in model.requests[0]
    finally:
        core.close()


def test_external_visual_judge_is_separate_host_report(tmp_path):
    model = FakeModel([plan(), drawing(), review()])
    core = NativeReasoningService(tmp_path / "core.db", model=model)
    seen = []
    def judge(path, subject):
        seen.append((Path(path).exists(), subject))
        return {"satisfactory": True, "feedback": "Observed bicycle"}
    try:
        result = SketchLab(core, visual_judge=judge).run(
            task_ref="evaluated", output_dir=tmp_path, max_attempts=3,
            backend="stdlib")
        assert result["attempts"] == 1
        assert result["final_status"] == "host_reported_satisfactory"
        assert result["visual_success_independently_verified"] is False
        assert seen == [(True, "a bicycle")]
    finally:
        core.close()


def test_online_references_pass_through_existing_research_interface(tmp_path):
    model = FakeModel([plan(), drawing(), review()])
    core = NativeReasoningService(tmp_path / "core.db", model=model)
    class ResearchStub:
        def __init__(self):
            self.calls = []
        def investigate(self, **kwargs):
            self.calls.append(kwargs)
            return {"sources": [{"url": "https://example.org/drawing"}]}
    research = ResearchStub()
    try:
        result = SketchLab(core, research=research).run(
            task_ref="online", output_dir=tmp_path, allow_online=True,
            max_attempts=1, backend="stdlib")
        assert result["references"] == ["https://example.org/drawing"]
        assert research.calls[0]["answer_with_model"] is False
        assert research.calls[0]["max_pages"] == 2
    finally:
        core.close()


@pytest.mark.parametrize("shapes", [
    [{"type": "script", "code": "evil()"}],
    [{"type": "line", "x1": "0;alert(1)", "y1": 0, "x2": 10, "y2": 10}],
    [{"type": "circle", "cx": 30, "cy": 30, "r": -1}],
    [{"type": "rect", "x": 1, "y": 1, "w": float("nan"), "h": 10}],
    [{"type": "polyline", "points": [[1, 1]]}],
])
def test_rejects_untrusted_model_commands(shapes):
    with pytest.raises(ValueError):
        validate_shapes(shapes)


def test_drawsvg_mit_backend_if_installed(tmp_path):
    pytest.importorskip("drawsvg")
    path = tmp_path / "drawsvg.svg"
    digest = draw_svg([{"type": "line", "x1": 10, "y1": 20,
                        "x2": 100, "y2": 90}], path, "drawsvg")
    assert digest and path.stat().st_size > 70
    assert "svg" in path.read_text().lower()


def test_model_required_and_online_off_by_default(tmp_path):
    core = NativeReasoningService(tmp_path / "core.db", model=None)
    try:
        with pytest.raises(ValueError):
            SketchLab(core).run(task_ref="no-model", output_dir=tmp_path)
    finally:
        core.close()


def test_cross_session_feedback_is_recalled_without_weight_training(tmp_path):
    db = tmp_path / "durable-core.db"
    first = FakeModel([plan("an old house"), drawing(), review()])
    core = NativeReasoningService(db, model=first)
    try:
        SketchLab(core).run(task_ref="first-sketch", output_dir=tmp_path / "one",
                            max_attempts=1, backend="stdlib")
    finally:
        core.close()
    second = FakeModel([plan("a new sailboat"), drawing(), review()])
    core = NativeReasoningService(db, model=second)
    try:
        result = SketchLab(core).run(task_ref="second-sketch",
                                    output_dir=tmp_path / "two",
                                    max_attempts=1, backend="stdlib")
        assert result["subject_chosen_by_BEAN_model"] == "a new sailboat"
        assert "an old house" in second.requests[0]
        assert "add handlebars" in second.requests[0]
        assert result["final_status"] == "unverified"
    finally:
        core.close()


def test_bean_may_end_when_self_satisfied_but_is_not_visual_verification(tmp_path):
    satisfied = ('{"claimed_subject":"bicycle","changes":"none",'
                 '"satisfied":true}')
    model = FakeModel([plan(), drawing(), satisfied])
    core = NativeReasoningService(tmp_path / "core.db", model=model)
    try:
        result = SketchLab(core).run(
            task_ref="self-satisfied", output_dir=tmp_path, max_attempts=4,
            backend="stdlib")
        assert result["attempts"] == 1
        assert result["final_status"] == "self_reported_satisfactory_unverified"
        assert result["visual_success_independently_verified"] is False
    finally:
        core.close()


def test_open_model_sketch_provider_uses_creative_json_not_reasoning_schema():
    class LocalClient:
        def __init__(self):
            self.calls = []
        def chat_json(self, model, messages, **kwargs):
            self.calls.append((model, messages, kwargs))
            return '{"subject":"a rainy garden","reference_query":""}'
    client = LocalClient()
    provider = OllamaSketchProvider(model_name="qwen2.5:1.5b", client=client)
    reply = provider.complete("Choose ANY subject to draw")
    assert reply["ok"] is True
    assert reply["adapter_name"] == "ollama"
    assert reply["model_name"] == "qwen2.5:1.5b"
    assert client.calls[0][2]["options"]["num_predict"] == 2048
    assert "schema" not in client.calls[0][2]  # NOT general reasoning response schema


def test_forced_iteration_budget_ignores_unverified_self_satisfaction(tmp_path):
    happy = ('{"claimed_subject":"bicycle","changes":"none",'
             '"satisfied":true}')
    model = FakeModel([plan(), drawing(), happy, drawing(), happy,
                       drawing(), happy])
    core = NativeReasoningService(tmp_path / "journal.sqlite3", model=model)
    try:
        result = SketchLab(core).run(
            task_ref="all-four-is-not-a-success-claim", output_dir=tmp_path / "out",
            max_attempts=3, complete_all_attempts=True, backend="stdlib")
        assert result["attempts"] == 3
        assert all(Path(row["metadata"]).exists() for row in result["history"])
        assert result["visual_success_independently_verified"] is False
        rows = [e for e in core.bank.journal.events()
                if e["kind"] == "trial" and
                e["data"].get("experiment") == "bean_sketch_v1"]
        assert len(rows) == 3
    finally:
        core.close()


def test_sketch_provider_reports_unreachable_local_model():
    class OfflineClient:
        def chat_json(self, *args, **kwargs):
            raise RuntimeError("local model not available")
    provider = OllamaSketchProvider(client=OfflineClient())
    outcome = provider.complete("Choose ANY subject")
    assert outcome["ok"] is False
    assert outcome["adapter_name"] == "ollama"
