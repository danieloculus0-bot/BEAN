"""Typed model-facing plan contract; compile references into native GoalCycle syntax.

The model still chooses tools, input values, and dependencies. The compiler only
translates explicit references; it does not invent observations or answers.
"""
import re

_FIELDS = {
    "numeric_context": ("history", "window"),
    "mean_sign": ("history",),
    "last_sign": ("history",),
    "compare_numeric": ("left", "right", "abs_tol", "rel_tol"),
}
_LIST_FIELDS = ("history",)
_NUMBER_FIELDS = ("mean", "last", "count", "prediction", "left", "right",
                  "absolute_difference", "abs_tol", "rel_tol")
_REFERENCE = re.compile(r"^@([0-7])\.([a-z_]+)$")


def _references(fields):
    return {"type": "string", "enum": [
        f"@{step}.{field}" for step in range(8) for field in fields]}


def _either(value_schema, fields):
    return {"anyOf": [value_schema, _references(fields)]}


def plan_schema(tool_names):
    """Constrain tool selection and numeric argument types, not the solution."""
    alternatives = []
    for name in sorted(tool_names):
        if name in _FIELDS:
            props = {}
            for field in _FIELDS[name]:
                if field == "history":
                    props[field] = _either(
                        {"type": "array", "items": {"type": "number"}}, _LIST_FIELDS)
                else:
                    props[field] = _either(
                        {"type": "integer" if field == "window" else "number"}, _NUMBER_FIELDS)
            required = list(_FIELDS[name])
            if name == "numeric_context":
                required.remove("window")
            args = {"type": "object", "properties": props,
                    "required": required, "additionalProperties": False}
        else:
            args = {"type": "object"}
        alternatives.append({
            "type": "object",
            "properties": {"tool": {"type": "string", "enum": [name]}, "args": args},
            "required": ["tool", "args"], "additionalProperties": False})
    return {"type": "object", "properties": {"steps": {
        "type": "array", "items": {"anyOf": alternatives}, "minItems": 1, "maxItems": 8}},
        "required": ["steps"], "additionalProperties": False}


def compile_typed_args(tool, args):
    """Translate only explicit typed argument slots; never modify text arguments."""
    if tool not in _FIELDS:
        return args
    result = dict(args)
    for key in _FIELDS[tool]:
        value = result.get(key)
        if not isinstance(value, str):
            continue
        match = _REFERENCE.fullmatch(value)
        if not match:
            continue
        step, field = match.groups()
        allowed = _LIST_FIELDS if key == "history" else _NUMBER_FIELDS
        if field not in allowed:
            raise ValueError(f"reference {value} is incompatible with {key}")
        result[key] = {"$step": int(step), "path": [field]}
    return result
