"""Opt-in, delayed-outcome inference of redundant sensor errors.

Only earlier verified outcomes may influence the current grouping. Missing feedback
is never treated as a negative outcome. This is a bounded synthetic research
adapter for OnlineSensorTrust, not an authenticated provenance detector or
production BEAN Core cognition.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from .sensor_reliability import OnlineSensorTrust, SensorObservation


@dataclass
class _Pair:
    n: float = 0.0
    a_wrong: float = 0.0
    b_wrong: float = 0.0
    both_wrong: float = 0.0


class OnlineDependencyLearner:
    """Estimate excess co-errors and group only mutually supported sources."""

    def __init__(self, trust: OnlineSensorTrust | None = None, *,
                 decay: float = 0.98, min_samples: float = 20.0,
                 min_coerrors: float = 3.0, min_excess: float = 0.10,
                 max_sources: int = 12, max_pairs: int = 120):
        if (not 0 < decay <= 1 or not 1 <= min_samples <= 1000
                or not 0 <= min_coerrors <= 1000 or not 0 < min_excess < 1
                or type(max_sources) is not int or not 2 <= max_sources <= 32
                or type(max_pairs) is not int or not 1 <= max_pairs <= 496):
            raise ValueError("invalid bounded dependency configuration")
        self.trust = trust if trust is not None else OnlineSensorTrust(decay=.97)
        self.decay, self.min_samples = decay, min_samples
        self.min_coerrors, self.min_excess = min_coerrors, min_excess
        self.max_sources, self.max_pairs = max_sources, max_pairs
        self.pairs: dict[tuple[str, str], _Pair] = {}
        self._pending: tuple[SensorObservation, ...] | None = None
        self.last_groups: dict[str, str] = {}

    def _dependent(self, a: str, b: str) -> bool:
        p = self.pairs.get(tuple(sorted((a, b))))
        if p is None or p.n < self.min_samples or p.both_wrong < self.min_coerrors:
            return False
        excess = p.both_wrong / p.n - (p.a_wrong / p.n) * (p.b_wrong / p.n)
        return excess >= self.min_excess

    def inferred_groups(self, origins: list[str] | tuple[str, ...]) -> dict[str, str]:
        """Deterministic complete-linkage clusters, not caller asserted truth."""
        names = sorted(origins)
        clusters: list[list[str]] = []
        for name in names:
            target = next((cluster for cluster in clusters
                           if all(self._dependent(name, other) for other in cluster)), None)
            if target is None:
                clusters.append([name])
            else:
                target.append(name)
        return {name: f"inferred_group_{i}" for i, cluster in enumerate(clusters)
                for name in cluster}

    def forecast(self, observations: list[SensorObservation]) -> float:
        if self._pending is not None:
            raise ValueError("previous prediction awaits feedback")
        if not isinstance(observations, (list, tuple)) or not observations:
            raise ValueError("observations required")
        names = [x.origin for x in observations if isinstance(x, SensorObservation)]
        if len(names) != len(observations) or len(names) > self.max_sources or len(set(names)) != len(names):
            raise ValueError("invalid source budget or duplicate origin")
        needed = set(combinations(sorted(names), 2)) - set(self.pairs)
        if len(self.pairs) + len(needed) > self.max_pairs:
            raise ValueError("pair history capacity exhausted")
        groups = self.inferred_groups(names)
        prediction = self.trust.forecast(observations, provenance_groups=groups)
        self._pending = tuple(observations)
        self.last_groups = groups
        return prediction

    def learn(self, outcome: int) -> None:
        if self._pending is None:
            raise ValueError("no prediction awaiting feedback")
        if type(outcome) is not int or outcome not in (0, 1):
            raise ValueError("binary verified outcome required")
        wrong = {o.origin: int(o.value != outcome) for o in self._pending}
        for a, b in combinations(sorted(wrong), 2):
            p = self.pairs.setdefault((a, b), _Pair())
            p.n = self.decay * p.n + 1
            p.a_wrong = self.decay * p.a_wrong + wrong[a]
            p.b_wrong = self.decay * p.b_wrong + wrong[b]
            p.both_wrong = self.decay * p.both_wrong + wrong[a] * wrong[b]
        self.trust.learn(outcome)
        self._pending = None

    def skip_feedback(self, *, reason: str) -> None:
        if self._pending is None:
            raise ValueError("no prediction awaiting feedback")
        self.trust.skip_feedback(reason=reason)
        self._pending = None
