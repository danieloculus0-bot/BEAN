"""Isolated NARS-inspired evidence revision prototype, not OpenNARS itself."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Evidence:
    event_id: str
    origin: str
    frequency: float
    confidence: float


class RevisableBelief:
    """Keep all receipts; revise only the latest independent vote per origin."""

    def __init__(self):
        self.history = []
        self._ids = set()

    def observe(self, event):
        if not isinstance(event, Evidence) or not event.event_id or not event.origin:
            raise ValueError("missing evidence identity")
        if event.event_id in self._ids:
            raise ValueError("duplicate event id")
        if not all(math.isfinite(x) and 0 <= x <= 1
                   for x in (event.frequency, event.confidence)):
            raise ValueError("frequency/confidence must be finite in [0,1]")
        self.history.append(event)
        self._ids.add(event.event_id)

    def prediction(self):
        latest = {}
        for event in self.history:
            latest[event.origin] = event
        if not latest:
            return 0.5
        weighted = []
        for event in latest.values():
            weight = event.confidence / max(1e-12, 1 - event.confidence)
            weighted.append((event.frequency, weight))
        total = sum(weight for _, weight in weighted)
        if total == 0:
            return 0.5
        frequency = sum(f * w for f, w in weighted) / total
        confidence = total / (total + 1)
        return 0.5 + confidence * (frequency - 0.5)

    def latest_prediction(self):
        return self.history[-1].frequency if self.history else 0.5
