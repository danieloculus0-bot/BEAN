"""Experimental Bayesian mixture over stationary and alternating observations.

No truth labels, scenario names, rewards, or lookahead enter this predictor.
Uses BEAN's experimental RevisableBelief history and two existing predictors.
This is an original lightweight hypothesis selector, NOT an external AI runtime.
"""
from __future__ import annotations
from math import exp, isfinite, lgamma, log
from .cognition import RevisableBelief


def _log_beta(a, b):
    return lgamma(a) + lgamma(b) - lgamma(a + b)


class PatternMixtureBelief:
    def __init__(self, *, window=11, prior_alternating=.10,
                 reliability_alpha=3., reliability_beta=1.):
        if type(window) is not int or not 6 <= window <= 100:
            raise ValueError("invalid window")
        if (type(prior_alternating) not in (int, float)
                or not isfinite(prior_alternating)
                or not 0 < prior_alternating < 1):
            raise ValueError("invalid prior")
        if any(type(v) not in (int, float) or not isfinite(v) or v <= 0
               for v in (reliability_alpha, reliability_beta)):
            raise ValueError("invalid reliability prior")
        self.base = RevisableBelief()
        self.window = window
        self.prior = float(prior_alternating)
        self.a = float(reliability_alpha)
        self.b = float(reliability_beta)

    def observe(self, evidence):
        self.base.observe(evidence)

    def pattern_posterior(self):
        sequence = [e.frequency for e in self.base.history[-self.window:]]
        if len(sequence) < self.window or any(v not in (0., 1.) for v in sequence):
            return 0.
        n = len(sequence)

        def log_evidence(alternating):
            branch = []
            for initial in (0, 1):
                matches = sum(value == (initial ^ (i % 2 if alternating else 0))
                              for i, value in enumerate(sequence))
                branch.append(_log_beta(self.a + matches, self.b + n - matches)
                              - _log_beta(self.a, self.b))
            maximum = max(branch)
            return maximum + log((exp(branch[0] - maximum)
                                  + exp(branch[1] - maximum)) / 2.)

        log_odds = (log(self.prior / (1 - self.prior))
                    + log_evidence(True) - log_evidence(False))
        return 1 / (1 + exp(-max(-50., min(50., log_odds))))

    def prediction(self):
        weight = self.pattern_posterior()
        return ((1 - weight) * self.base.prediction()
                + weight * self.base.latest_prediction())

    def latest_prediction(self):
        return self.base.latest_prediction()
