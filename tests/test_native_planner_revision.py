import json
import pytest
from bean.runtime.plan_contracts import compile_arguments, revision_feedback

TOOLS = {name: None for name in ("last_sign", "mean_sign", "compare_numeric", "profile_csv")}
INPUTS = {"history": [-2, 4, 6, 8]}


def test_compiler_normalizes_real_failed_plan_without_executing():
    raw = json.dumps({"steps": [
        {"tool": "last_sign", "args": {"history": {"$input": ["history"]}}},
        {"tool": "mean_sign", "args": {"history": "$input[0]"}},
        {"tool": "compare_numeric", "args": {"left": {"$step": 0, "path": []},
         "right": "$step:1.output", "abs_tol": 0, "rel_tol": 0}}]})
    result = compile_arguments(raw, INPUTS, TOOLS)
    assert result[1]["args"]["history"] == {"$input": ["history"]}
    assert result[2]["args"]["left"] == {"$step": 0, "path": ["prediction"]}
    assert result[2]["args"]["right"] == {"$step": 1, "path": ["prediction"]}


def test_failed_plan_gets_specific_step_and_full_proposal_back():
    raw = json.dumps({"steps": [
        {"tool": "last_sign", "args": {"history": ["$input[0][-1]"]}}]})
    with pytest.raises(ValueError, match=r"step 0 \(last_sign\)") as exc:
        compile_arguments(raw, INPUTS, TOOLS)
    feedback = revision_feedback(raw, str(exc.value), INPUTS)
    evidence = json.loads(feedback.split("\n")[-1])
    assert evidence["rejected_plan"] == raw
    assert evidence["available_input_bindings"] == {"history": {"$input": ["history"]}}
    assert "required args=history" in evidence["error"]


@pytest.mark.parametrize("raw", [
    '{"steps":[],"steps":[]}',
    '{"steps":[{"tool":"last_sign","args":{"history":[NaN]}}]}',
    '{"steps":[{"tool":[],"args":{}}]}',
    '{"steps":[{"tool":"missing","args":{}}]}',
    '{"steps":[{"tool":"last_sign","args":{"history":{"$step":0}}}]}',
    '{"steps":[{"tool":"last_sign","args":{"history":{"$input":["absent"]}}}]}',
])
def test_invalid_plans_remain_rejected(raw):
    with pytest.raises(ValueError):
        compile_arguments(raw, INPUTS, TOOLS)


def test_literal_text_not_reinterpreted():
    raw = json.dumps({"steps": [{"tool": "profile_csv", "args": {"text": "$input[0]"}}]})
    assert compile_arguments(raw, INPUTS, TOOLS)[0]["args"]["text"] == "$input[0]"
