"""Brain 0.12 OpenAI provider tests.

These tests do not call the live API.
"""

from __future__ import annotations

from bean.reasoning.providers.openai_provider import OPENAI_RESPONSES_URL, OpenAIProvider


def test_schema_is_strict_and_closed():
    provider = OpenAIProvider(api_key="test")
    schema = provider._json_schema()
    assert schema["additionalProperties"] is False
    req = provider._build_request({"motion_enabled": False}, "test")
    fmt = req["text"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["strict"] is True


def test_uses_responses_endpoint_constant():
    assert OPENAI_RESPONSES_URL.endswith("/v1/responses")


def test_parse_valid_output():
    provider = OpenAIProvider(api_key="test")
    text = '{"reasoning_text":"Reasoning only.","summary":"Safe.","confidence":0.5,"referenced_hypothesis_ids":[],"action_candidates":[{"action_type":"defer","rationale":"Wait.","payload":{},"risk_level":"low"}]}'
    output = provider._parse_output(text)
    assert output.error is None
    assert len(output.action_candidates) == 1


def test_parse_unknown_action_type_rejected():
    provider = OpenAIProvider(api_key="test")
    text = '{"reasoning_text":"Reasoning only.","summary":"Safe.","confidence":0.5,"referenced_hypothesis_ids":[],"action_candidates":[{"action_type":"execute_motion","rationale":"bad","payload":{},"risk_level":"low"}]}'
    output = provider._parse_output(text)
    assert len(output.action_candidates) == 0
    assert output.error is not None


def test_forbidden_language_redacted():
    provider = OpenAIProvider(api_key="test")
    text = '{"reasoning_text":"I am sentient.","summary":"bad","confidence":0.9,"referenced_hypothesis_ids":[],"action_candidates":[]}'
    output = provider._parse_output(text)
    assert output.confidence == 0.0
    assert output.error is not None


def test_refusal_and_incomplete_raise():
    provider = OpenAIProvider(api_key="test")
    try:
        provider._extract_text({"output": [{"content": [{"type": "refusal", "refusal": "no"}]}]})
    except ValueError:
        pass
    else:
        raise AssertionError("refusal accepted")
    try:
        provider._extract_text({"status": "incomplete", "output": []})
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete accepted")


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    failed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"PASS {name}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
            import traceback
            traceback.print_exc()
    print(f"{len(tests) - failed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
