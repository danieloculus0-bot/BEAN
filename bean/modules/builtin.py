"""Initial native BEAN cognition blocks, using the same callable contract."""
from __future__ import annotations

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
    from bean.memory.event_logger import get_recent_events
    session = data["session_uuid"]
    events = get_recent_events(session, limit=int(data.get("limit", 8)))
    return {"events": events, "count": len(events)}


BLOCKS = [
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
