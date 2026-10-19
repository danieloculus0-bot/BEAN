"""Initial native BEAN cognition blocks, using the same callable contract."""
from __future__ import annotations

import json
from statistics import mean


def numeric_context(data: dict, context: dict) -> dict:
    """Turn a sequence of observations into reusable analysis features."""
    history = [float(v) for v in data.get("history", [])]
    window = max(1, int(data.get("window", 12)))
    sample = history[-window:]
    return {
        "history": history,
        "count": len(history),
        "mean": mean(sample) if sample else None,
        "last": history[-1] if history else None,
        "trend": (
            "up" if sum(sample) > 0 else "down" if sum(sample) < 0 else "flat"
        ) if sample else "unknown",
    }


def memory_recall(data: dict, context: dict) -> dict:
    """Access native local BEAN session memory as a drop-in cognition block."""
    from bean.memory.event_logger import get_recent_events, parse_event_data
    session = data["session_uuid"]
    events = get_recent_events(session, limit=int(data.get("limit", 8)))
    # Core's SQLite event API returns data as its stored JSON string. The
    # Bridge output port should expose the actual structured observation,
    # otherwise downstream blocks cannot address data.temperature_c, etc.
    for event in events:
        raw = event.get("data")
        if isinstance(raw, str):
            try:
                event["data"] = json.loads(raw)
            except ValueError:
                event["data_parse_error"] = True
                # Preserve the original observation, even if malformed.
        elif raw is None:
            event["data"] = None
    return {"events": events, "count": len(events)}


def predict_last_sign(data: dict, context: dict) -> dict:
    """A simple fast predictor for a stream of observed changes."""
    history = [float(v) for v in data["history"]]
    if not history:
        raise ValueError("history needs observations")
    return {"prediction": int(history[-1] > 0), "method": "last_observation"}


def predict_mean_sign(data: dict, context: dict) -> dict:
    """An alternative predictor for the same task, using the mean trend."""
    history = [float(v) for v in data["history"]]
    if not history:
        raise ValueError("history needs observations")
    return {"prediction": int(mean(history) > 0), "method": "mean_observation"}


BLOCKS = [
    {
        "name": "bean.last_sign",
        "entrypoint": "bean.modules.builtin:predict_last_sign",
        "capabilities": ["binary_forecast"],
        "description": "Predict sign from most recent observation",
    },
    {
        "name": "bean.mean_sign",
        "entrypoint": "bean.modules.builtin:predict_mean_sign",
        "capabilities": ["binary_forecast"],
        "description": "Predict sign from mean of observations",
    },
    {
        "name": "bean.numeric_context",
        "entrypoint": "bean.modules.builtin:numeric_context",
        "capabilities": ["numeric_context", "data_analysis"],
        "description": "Analyze an observed numeric series for a later block",
    },
    {
        "name": "bean.memory_recall",
        "entrypoint": "bean.modules.builtin:memory_recall",
        "capabilities": ["memory_recall"],
        "description": "Recall recorded events from local BEAN memory",
    },
]


def register_builtin(runtime) -> None:
    for block in BLOCKS:
        runtime.register(block)
