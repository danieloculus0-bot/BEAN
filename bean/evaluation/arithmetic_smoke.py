"""Bounded addition-smoke grading: factual value and output format are separate.

Only a complete integer or the exact requested addition equation is parsed.
Never search for an expected digit inside arbitrary prose or execute model text.
"""
from __future__ import annotations

import re


def grade_addition(answer, left: int, right: int) -> dict:
    if any(type(v) is not int or abs(v) > 1_000_000 for v in (left, right)):
        raise ValueError("bounded integer addition operands required")
    expected = left + right
    observed = None
    representation = "unrecognized"
    if isinstance(answer, str) and len(answer) <= 100:
        text = answer.strip()
        if re.fullmatch(r"[+-]?[0-9]{1,12}", text):
            observed = int(text)
            representation = "integer"
        else:
            pattern = (re.escape(str(left)) + r"\s*\+\s*" + re.escape(str(right))
                       + r"\s*=\s*([+-]?[0-9]{1,12})")
            match = re.fullmatch(pattern, text)
            if match:
                observed = int(match.group(1))
                representation = "faithful_equation"
    return {"schema": "bean.addition.smoke_grade.v1", "expected_value": expected,
            "observed_value": observed, "representation": representation,
            "answer_correct": observed == expected if observed is not None else False,
            "single_numeral_format": representation == "integer"}
