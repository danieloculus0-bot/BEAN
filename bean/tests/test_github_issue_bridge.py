"""GitHub BEAN request parsing, ownership, result transport, native Core reuse."""
import json

import pytest

from scripts.bean_github_issue_bridge import (
    from_github_event, parse_public_request, render_public_reply,
)
from scripts.invoke_bean import serve_public_request


def envelope(command="reasoning_status", args=None):
    return {"schema": "bean.github.request.v1", "command": command,
            "args": {} if args is None else args}


def event(body, *, action="opened", author="danieloculus0-bot"):
    return {
        "action": action,
        "sender": {"login": author},
        "issue": {
            "number": 42, "title": "[BEAN] public request",
            "user": {"login": "danieloculus0-bot"},
            "body": body,
        },
    }


def test_exact_public_status_request_and_issue_identity():
    payload = from_github_event(event(json.dumps(envelope())), "issues")
    assert payload["request_id"] == "issue-42"
    assert payload["request"]["command"] == "reasoning_status"


def test_markdown_json_envelope_and_comment_request():
    body = json.dumps(envelope("reasoning_local", {
        "domain": "synthetic", "task_ref": "test-1",
        "query": "If test value is 4, what happens?",
    }))
    data = event("ignored", action="created")
    data["comment"] = {"id": 123, "user": {"login": "danieloculus0-bot"},
                       "body": chr(96) * 3 + "json\n" + body + "\n" + chr(96) * 3}
    assert from_github_event(data, "issue_comment")["request_id"] == "comment-123"


def test_reject_nonowner_and_foreign_issue():
    data = event(json.dumps(envelope()), author="outsider")
    with pytest.raises(ValueError, match="owner"):
        from_github_event(data, "issues")
    data = event(json.dumps(envelope()))
    data["issue"]["user"]["login"] = "outsider"
    with pytest.raises(ValueError, match="owner"):
        from_github_event(data, "issues")
    data = event(json.dumps(envelope()))
    data["issue"]["pull_request"] = {"url": "public"}
    with pytest.raises(ValueError):
        from_github_event(data, "issues")


@pytest.mark.parametrize("bad", [
    {"schema": "bean.github.request.v1", "command": "log_note", "args": {}},
    {"schema": "wrong", "command": "reasoning_status", "args": {}},
    {"schema": "bean.github.request.v1", "command": "reasoning_status",
     "args": {"unexpected": "value"}},
    {"schema": "bean.github.request.v1", "command": "reasoning_recall",
     "args": {"domain": "general", "query": "x", "limit": 99}},
    {"schema": "bean.github.request.v1", "command": "reasoning_local",
     "args": {"domain": "x", "task_ref": "y", "query": ""}},
])
def test_bad_commands_fail_closed(bad):
    with pytest.raises(ValueError):
        parse_public_request(json.dumps(bad))


def test_public_request_size_rejected():
    with pytest.raises(ValueError, match="3 KB"):
        parse_public_request("x" * 3001)


def test_actual_native_reasoning_status(tmp_path):
    status = serve_public_request(tmp_path / "native.db", envelope())
    assert status["schema"] == "bean.native.reasoning.status.v1"
    assert status["model_configured"] is False
    assert status["hosted_connector_integrated"] is False


def test_reply_is_marked_and_html_escaped():
    body = render_public_reply("issue-42", {
        "schema": "bean.github.reply.v1", "command": "reasoning_local",
        "generation": 4, "receipt_sha256": "a" * 64,
        "response": {"text": "<script>alert(1)</script>"},
    })
    assert "<!-- BEAN_REPLY:issue-42 -->" in body
    assert "&lt;script&gt;" in body
    assert "<script>" not in body


def test_no_fake_provider_or_arbitrary_shell(tmp_path):
    with pytest.raises(ValueError, match="Unsupported"):
        serve_public_request(tmp_path / "native.db", envelope("log_note"))


def test_standalone_cli_responds_to_real_core_request(tmp_path):
    """Reproduce the GitHub Actions direct-script invocation path, not a module import."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    request_file = tmp_path / "request.json"
    reply_file = tmp_path / "reply.json"
    request_file.write_text(json.dumps(envelope()), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "invoke_bean.py"),
         "--state-dir", str(tmp_path / "checkpoint"),
         "--runtime-dir", str(tmp_path / "runtime"),
         "--ticks", "12",
         "--request-file", str(request_file),
         "--reply-file", str(reply_file)],
        cwd=tmp_path, capture_output=True, text=True, timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    reply = json.loads(reply_file.read_text(encoding="utf-8"))
    assert reply["schema"] == "bean.github.reply.v1"
    assert reply["response"]["schema"] == "bean.native.reasoning.status.v1"
    assert reply["generation"] == 1
    assert reply["external_model_invoked"] is False
    assert (tmp_path / "checkpoint" / "manifest.json").exists()
