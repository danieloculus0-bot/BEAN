"""Experimental volatility-adaptive evidence selection, not an external AI runtime.

Uses existing RevisableBelief receipts and its two unchanged predictors.
The switch uses observed disagreement only, never ground-truth labels.
"""
from __future__ import annotations
import math
from .cognition import RevisableBelief


class VolatilityAdaptiveBelief:
    """Use newest evidence in volatile conditions; revise when stable."""

    def __init__(self, *, threshold=0.65, window=11, min_history=8):
        if not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("threshold must be a finite fraction")
        if type(window) is not int or type(min_history) is not int or not 3 <= min_history <= window <= 100:
            raise ValueError("invalid observation window")
        self.threshold = float(threshold)
        self.window = window
        self.min_history = min_history
        self.base = RevisableBelief()

    def observe(self, event):
        self.base.observe(event)

    def volatility(self):
        recent = self.base.history[-self.window:]
        if len(recent) < 2:
            return 0.0
        return sum(abs(a.frequency - b.frequency) for a, b in zip(recent, recent[1:])) / (len(recent) - 1)

    def mode(self):
        return ("newest" if len(self.base.history) >= self.min_history and
                self.volatility() >= self.threshold else "revision")

    def prediction(self):
        if self.mode() == "newest":
            return self.base.latest_prediction()
        return self.base.prediction()
