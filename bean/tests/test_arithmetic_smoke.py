"""Wrong values and incidental expected digits cannot pass factual grading."""
import pytest

from bean.evaluation.arithmetic_smoke import grade_addition


@pytest.mark.parametrize("answer,correct,format_ok", [
    ("4", True, True), (" 4\n", True, True),
    ("2 + 2 = 4", True, False), ("2+2=4", True, False),
    ("2", False, True), ("14", False, True), ("-4", False, True),
    ("2+2=2", False, False), ("2+2=14", False, False),
    ("1+3=4", False, False), ("4 or 2", False, False),
    ("The answer is 4", False, False), ("2 (expected 4)", False, False),
    ("4\n2", False, False), ("2+2=4=2", False, False),
    ("", False, False), (None, False, False),
    (4, False, False), ("4" * 101, False, False),
    ("__import__('os').system('echo 4')", False, False),
])
def test_factual_value_is_distinct_from_format(answer, correct, format_ok):
    result = grade_addition(answer, 2, 2)
    assert result["expected_value"] == 4
    assert result["answer_correct"] is correct
    assert result["single_numeral_format"] is format_ok


def test_grader_is_bound_to_the_requested_operands():
    assert grade_addition("-2 + 5 = 3", -2, 5)["answer_correct"] is True
    assert grade_addition("2 + 1 = 3", -2, 5)["answer_correct"] is False
    assert grade_addition("2 + 2 = 4", 3, 5)["answer_correct"] is False


@pytest.mark.parametrize("left,right", [(True, 2), (2.0, 2), (None, 2), (10**7, 2)])
def test_invalid_operand_contract(left, right):
    with pytest.raises(ValueError):
        grade_addition("4", left, right)
