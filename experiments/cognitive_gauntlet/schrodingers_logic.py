"""Schrodinger's Logic: two concurrent evidence states, one chaos-triggered choice.

Both existing BEAN experimental sensor-trust learners continuously receive the
same evidence and *delayed* feedback. Only when their recent scored forecasts
strongly diverge in utility and source reliability does the output consult
both states. Long-term knowledge is never deleted by the short-term branch.

The name is a metaphor for competing hypotheses, NOT quantum computing.
The feedback and provenance are host-supplied, not independently verified.
"""
from __future__ import annotations
from collections import deque
import math
from .sensor_reliability import OnlineSensorTrust


class SchrodingersLogic:
    def __init__(self, *, short_decay=.97, window=12, min_history=18,
                 entry_advantage=.025, exit_advantage=-.005,
                 entry_gap=.075, exit_gap=.035, short_weight=.80):
        if (type(window) is not int or type(min_history) is not int
                or not 4 <= window <= min_history <= 100):
            raise ValueError("invalid evidence window")
        numbers = (short_decay, entry_advantage, exit_advantage,
                   entry_gap, exit_gap, short_weight)
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in numbers):
            raise ValueError("non-finite chaos parameters")
        if not (0 < short_decay < 1 and
                -1 <= exit_advantage < entry_advantage <= 1 and
                0 <= exit_gap < entry_gap <= 1 and 0 < short_weight <= 1):
            raise ValueError("invalid chaos parameters")
        self.long_memory = OnlineSensorTrust()
        self.short_memory = OnlineSensorTrust(decay=short_decay)
        self.window = window
        self.min_history = min_history
        self.entry_advantage = float(entry_advantage)
        self.exit_advantage = float(exit_advantage)
        self.entry_gap = float(entry_gap)
        self.exit_gap = float(exit_gap)
        self.short_weight = float(short_weight)
        self.recent_scores = deque(maxlen=window)
        self.chaos = False
        self.trials = 0
        self.receipts = []
        self._pending = None

    def forecast(self, observations):
        if self._pending is not None:
            raise ValueError("feedback required before new forecast")
        # The existing learner checks all origin names and unique event IDs.
        long_prediction = self.long_memory.forecast(observations)
        short_prediction = self.short_memory.forecast(observations)
        n = len(self.recent_scores)
        recent_advantage = (sum(long - short for long, short in self.recent_scores) / n
                            if n else 0.0)
        source_gap = sum(abs(self.long_memory.reliability(x.origin) -
                             self.short_memory.reliability(x.origin))
                         for x in observations) / len(observations)
        if self.trials >= self.min_history and n == self.window:
            if not self.chaos:
                self.chaos = (recent_advantage >= self.entry_advantage and
                              source_gap >= self.entry_gap)
            else:
                self.chaos = (recent_advantage >= self.exit_advantage and
                              source_gap >= self.exit_gap)
        else:
            self.chaos = False
        combined = ((1-self.short_weight)*long_prediction +
                    self.short_weight*short_prediction if self.chaos
                    else long_prediction)
        self._pending = {
            "long_prediction": long_prediction,
            "short_prediction": short_prediction,
            "prediction": combined,
            "mode": "parallel_chaos" if self.chaos else "remember",
            "recent_advantage": recent_advantage,
            "source_gap": source_gap,
            "evidence_ids": [x.evidence_id for x in observations],
        }
        return combined

    def diagnostics(self):
        if self._pending is None:
            raise ValueError("call forecast before diagnostics")
        return dict(self._pending)

    def learn(self, outcome):
        if self._pending is None:
            raise ValueError("no forecast awaiting feedback")
        if type(outcome) is not int or outcome not in (0, 1):
            raise ValueError("binary outcome expected")
        item = dict(self._pending)
        self.recent_scores.append(((item["long_prediction"]-outcome)**2,
                                   (item["short_prediction"]-outcome)**2))
        self.long_memory.learn(outcome)
        self.short_memory.learn(outcome)
        self.receipts.append({
            "evidence_ids": item["evidence_ids"],
            "mode": item["mode"],
            "prediction": item["prediction"],
            "outcome_after_forecast": outcome,
            "loss": (item["prediction"] - outcome)**2,
        })
        self.trials += 1
        self._pending = None

    def state(self):
        if self._pending is not None:
            raise ValueError("cannot checkpoint with pending outcome")
        return {
            "schema": "bean.cognitive_gauntlet.schrodingers_logic.v1",
            "window": self.window,
            "min_history": self.min_history,
            "entry_advantage": self.entry_advantage,
            "exit_advantage": self.exit_advantage,
            "entry_gap": self.entry_gap, "exit_gap": self.exit_gap,
            "short_weight": self.short_weight,
            "long_memory": self.long_memory.state(),
            "short_memory": self.short_memory.state(),
            "recent_scores": [list(x) for x in self.recent_scores],
            "chaos": self.chaos,
            "trials": self.trials,
            "receipts": list(self.receipts),
        }

    @classmethod
    def restore(cls, state):
        if not isinstance(state, dict) or state.get("schema") != "bean.cognitive_gauntlet.schrodingers_logic.v1":
            raise ValueError("invalid dual-state schema")
        short = OnlineSensorTrust.restore(state["short_memory"])
        model = cls(short_decay=short.decay, window=state["window"],
                    min_history=state["min_history"],
                    entry_advantage=state["entry_advantage"],
                    exit_advantage=state["exit_advantage"],
                    entry_gap=state["entry_gap"], exit_gap=state["exit_gap"],
                    short_weight=state["short_weight"])
        model.long_memory = OnlineSensorTrust.restore(state["long_memory"])
        if model.long_memory.decay != 1.:
            raise ValueError("long-term memory has been modified")
        recent = state["recent_scores"]
        if not isinstance(recent, list) or len(recent) > model.window:
            raise ValueError("invalid score history")
        for pair in recent:
            if (not isinstance(pair, list) or len(pair) != 2 or
                    any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
                        for v in pair)):
                raise ValueError("invalid score receipt")
        model.recent_scores = deque((tuple(x) for x in recent), maxlen=model.window)
        model.trials = state["trials"]
        model.chaos = state["chaos"]
        model.receipts = list(state["receipts"])
        if (type(model.trials) is not int or model.trials < 0 or
                type(model.chaos) is not bool or
                len(model.receipts) != model.trials or
                model.trials != len(model.long_memory.receipts) or
                model.trials != len(model.short_memory.receipts)):
            raise ValueError("invalid dual-state replay lengths")
        return model
