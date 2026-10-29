"""Shared evidence models for isolated BEAN cognitive experiments."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Evidence:
    event_id: str
    origin: str
    frequency: float
    confidence: float
