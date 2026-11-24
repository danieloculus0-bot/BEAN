"""Original BEAN preflight: validate known data contracts before GoalCycle.

No tool is executed by the compiler. Unresolved prior-step data is deferred
until the actual result exists. Unknown tool contracts retain existing behavior.
"""
import math

DEFERRED = object()

# Explicit contracts for existing registered native tools, not inferred from prose.
CONTRACTS = {
    "last_sign": ({"history": "history"}, {}),
    "mean_sign": ({"history": "history"}, {}),
    "numeric_context": ({"history": "history"}, {"window": "window"}),
    "compare_numeric": ({"left": "number", "right": "number",
                         "abs_tol": "nonnegative", "rel_tol": "relative"}, {}),
    "profile_csv": ({"text": "text"}, {}),
    "group_csv_sum": ({"text": "text", "group": "name", "value": "name"}, {}),
    "search_transcript": ({"records": "list", "query": "name"}, {"limit": "limit"}),
    "search_registered_skills": ({"query": "name"}, {"limit": "limit"}),
}


def read_path(value, path):
    if not isinstance(path, list) or len(path) > 32:
        raise ValueError("invalid reference path")
    for key in path:
        if isinstance(value, dict) and type(key) is str and key in value:
            value = value[key]
        elif isinstance(value, list) and type(key) is int and 0 <= key < len(value):
            value = value[key]
        else:
            raise ValueError("reference path is absent or has incompatible type")
    return value


def preview(value, inputs, prior_tools):
    if isinstance(value, dict):
        if "$input" in value:
            if set(value) != {"$input"}:
                raise ValueError("invalid input reference")
            return read_path(inputs, value["$input"])
        if "$step" in value:
            if set(value) - {"$step", "path"} or type(value["$step"]) is not int:
                raise ValueError("invalid step reference")
            index = value["$step"]
            if not 0 <= index < len(prior_tools):
                raise ValueError("step reference must point backward")
            path = value.get("path", [])
            if not isinstance(path, list) or len(path) > 32 or any(
                    type(key) not in (str, int) or (type(key) is int and key < 0)
                    for key in path):
                raise ValueError("invalid output reference path")
            # Reject impossible field names for exact, stable output contracts.
            outputs = {"last_sign": {"prediction", "method"},
                       "mean_sign": {"prediction", "method"},
                       "numeric_context": {"history", "count", "mean", "last", "trend"}}
            fields = outputs.get(prior_tools[index])
            if path and fields is not None and (type(path[0]) is not str or path[0] not in fields):
                raise ValueError("prior tool has no such output field")
            return DEFERRED
        return {k: preview(v, inputs, prior_tools) for k, v in value.items()}
    if isinstance(value, list):
        return [preview(v, inputs, prior_tools) for v in value]
    return value


def finite(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def valid(kind, value):
    if value is DEFERRED:
        return True
    if kind == "history":
        return (isinstance(value, list) and 0 < len(value) <= 10000
                and all(v is DEFERRED or finite(v) for v in value))
    if kind == "number":
        return finite(value)
    if kind == "nonnegative":
        return finite(value) and value >= 0
    if kind == "relative":
        return finite(value) and 0 <= value < 1
    if kind == "window":
        return type(value) is int and 1 <= value <= 10000
    if kind == "limit":
        return type(value) is int and 1 <= value <= 20
    if kind == "text":
        return isinstance(value, str) and len(value) <= 64000
    if kind == "name":
        return isinstance(value, str) and 0 < len(value.strip()) <= 512
    if kind == "list":
        return isinstance(value, list)
    raise ValueError("unknown host contract kind")


def validate_args(tool, args):
    if not isinstance(args, dict):
        raise ValueError("arguments must be an object")
    if tool not in CONTRACTS:
        return
    required, optional = CONTRACTS[tool]
    if not set(required) <= set(args) or set(args) - set(required) - set(optional):
        raise ValueError(tool + " argument names do not match contract")
    for key, value in args.items():
        if not valid((required | optional)[key], value):
            raise ValueError(tool + " invalid argument: " + key)


def preflight(tool, args, inputs, prior_tools):
    validate_args(tool, preview(args, inputs, prior_tools))
