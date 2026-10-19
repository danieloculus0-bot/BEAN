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


def observe_experiment(data: dict, context: dict) -> dict:
    """Turn observed, locally testable uncertainty into a Core curiosity record.

    The outcome is supplied as observed data, never guessed by a generator.
    Bridge decides which installed module to run in response.
    """
    import json
    from bean.memory.store import get_store
    from bean.memory.event_logger import EventType, Source, log_event

    session_uuid = data.get("session_uuid") or context["session_uuid"]
    capability = data["capability"]
    inputs = data["inputs"]
    expected = data["expected_output"]
    question = data.get("question") or f"Which {capability} method explains the observed result?"
    if not isinstance(capability, str) or not isinstance(inputs, dict) or not isinstance(expected, dict):
        raise ValueError("experiment requires capability, inputs and observed output")
    payload = {
        "schema": "bean.cognition.experiment.v1",
        "capability": capability,
        "inputs": inputs,
        "expected_output": expected,
    }
    event_id = log_event(
        session_uuid, EventType.OBSERVATION,
        "An observable experiment question was encountered.",
        Source.SYSTEM, subtype="cognitive_experiment_observed",
        data={"question": question, **payload},
    )
    store = get_store()
    cursor = store.execute(
        "INSERT INTO curiosity (question, context, status) VALUES (?, ?, 'open')",
        (question, json.dumps(payload, sort_keys=True)),
    )
    store.commit()
    return {"question_id": cursor.lastrowid, "event_id": event_id,
            "capability": capability, "status": "open"}


def evaluate_drives(data: dict, context: dict) -> dict:
    """Expose Core's existing drive signals as Bridge-readable observations."""
    from bean.cognition.drive import DriveEvaluator
    session_uuid = data.get("session_uuid") or context["session_uuid"]
    states = DriveEvaluator().evaluate_all(session_uuid)
    return {"states": [state.to_dict() for state in states],
            "threatened": [state.name for state in states if state.is_threatened()]}


def reason_about(data: dict, context: dict) -> dict:
    """Use the native Core reasoning engine with a named local provider."""
    from bean.reasoning.reasoning_engine import ReasoningEngine
    session_uuid = data.get("session_uuid") or context["session_uuid"]
    outcome = ReasoningEngine().run(
        session_uuid,
        request_type=data.get("request_type", "reflection"),
        source_event_id=data.get("source_event_id"),
        adapter_name=data.get("adapter_name", "ollama"),
    )
    return outcome


BLOCKS = [
    {
        "name": "bean.observe_experiment",
        "entrypoint": "bean.modules.builtin:observe_experiment",
        "capabilities": ["observe_experiment"],
        "description": "Record a structured, observed test as an open curiosity question",
    },
    {
        "name": "bean.drive_evaluation",
        "entrypoint": "bean.modules.builtin:evaluate_drives",
        "capabilities": ["drive_evaluation"],
        "description": "Read BEAN's existing drive pressures",
    },
    {
        "name": "bean.reasoning",
        "entrypoint": "bean.modules.builtin:reason_about",
        "capabilities": ["reasoning"],
        "description": "Use existing Core model reasoning with recorded observations",
    },
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
