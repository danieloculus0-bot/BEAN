"""Shared evidence models for isolated BEAN cognitive experiments."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Evidence:
    event_id: str
    origin: str
    frequency: float
    confidence: float


class RevisableBelief:
    def __init__(self):
        self.history = []

    def observe(self, event):
        self.history.append(event)

    def prediction(self):
        return self.history[-1].frequency if self.history else 0.5

    def latest_prediction(self):
        return self.prediction()
