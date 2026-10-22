"""Episodic action arbitration over BEAN's existing SpongeTD Q-values.

Domain-neutral: caller supplies opaque state, legal actions, and optional
candidate next-location references. No model download, network call or actions.
"""
from __future__ import annotations
from collections import Counter, deque
import math
import random


class SpongeIntuition:
    """Read-only Q arbitration with local loop escape, reset every episode."""

    def __init__(self, policy, *, seed=0, visit_penalty=0.5,
                 revisit_penalty=0.2, lookback=10):
        if not all(hasattr(policy, name) for name in ("q", "actions", "key")):
            raise TypeError("SpongeTD-compatible policy required")
        if any(type(x) not in (int, float) or not math.isfinite(x) or x < 0
               for x in (visit_penalty, revisit_penalty)):
            raise ValueError("penalties must be finite nonnegative")
        if type(lookback) is not int or not 1 <= lookback <= 200:
            raise ValueError("lookback outside 1..200")
        self.policy = policy
        self.rng = random.Random(seed)
        self.visit_penalty = float(visit_penalty)
        self.revisit_penalty = float(revisit_penalty)
        self.recent = deque(maxlen=lookback)
        self.visits = Counter()
        self.last_decision = None
        self.decisions = 0

    def choose(self, state, *, location_ref, legal_actions,
               candidate_destinations=None):
        """Select the highest adjusted Q-value without changing policy.q.

        legal_actions are indices into policy.actions. The optional destination
        hints must exist before the decision, never from actual future outcomes.
        """
        key = self.policy.key(state)
        location = self.policy.key(location_ref)
        if not isinstance(legal_actions, (tuple, list)) or not legal_actions:
            raise ValueError("legal_actions must be nonempty")
        if (any(type(a) is not int or not 0 <= a < len(self.policy.actions)
                for a in legal_actions) or len(set(legal_actions)) != len(legal_actions)):
            raise ValueError("Invalid or duplicated available action")
        if candidate_destinations is not None:
            if (not isinstance(candidate_destinations, dict)
                    or any(type(a) is not int or a not in legal_actions
                           for a in candidate_destinations)):
                raise ValueError("Invalid candidate destinations")
        values = self.policy.q.get(key, [0.0] * len(self.policy.actions))
        candidates = []
        for action in legal_actions:
            attempts = self.visits[(location, action)]
            next_ref = (
                self.policy.key(candidate_destinations[action])
                if candidate_destinations is not None
                and action in candidate_destinations else None)
            loops = sum(ref == next_ref for ref in self.recent) if next_ref else 0
            adjusted = (values[action] - self.visit_penalty * attempts
                        - self.revisit_penalty * loops)
            candidates.append((adjusted, action, attempts, loops))
        high = max(item[0] for item in candidates)
        tied = [item for item in candidates if abs(item[0] - high) <= 1e-12]
        winning = self.rng.choice(tied)
        self.visits[(location, winning[1])] += 1
        self.recent.append(location)
        self.decisions += 1
        self.last_decision = {
            "action": self.policy.actions[winning[1]],
            "q_value": float(values[winning[1]]),
            "prior_local_attempts": winning[2],
            "predicted_recent_revisits": winning[3],
            "adjusted_value": float(winning[0]),
            "source": "SpongeTD Q-value plus episodic novelty",
        }
        return winning[1]
