"""Opt-in discovery index and progressive repeat-scan planning.

The discovery index's counter represents eligible *potential candidates*,
NOT validated matches. Text, intimate preferences, images, mental health,
and other private human data are not indexed.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import heapq
import math

from .protocol import DETAILS, TOPICS


@dataclass(frozen=True)
class AnonymousCandidate:
    agent_id: str
    tags: frozenset[tuple[str, str]]
    ready: bool = False
    active: bool = False
    consent: bool = False
    adult_confirmed: bool = False

    def __post_init__(self):
        if (not isinstance(self.agent_id, str) or not self.agent_id.isascii()
                or not 1 <= len(self.agent_id) <= 64):
            raise ValueError("invalid anonymous agent id")
        if any(type(x) is not bool for x in (
                self.ready, self.active, self.consent, self.adult_confirmed)):
            raise ValueError("explicit lifecycle flags required")
        if not isinstance(self.tags, frozenset) or any(
                not isinstance(tag, tuple) or len(tag) != 2
                or tag[0] not in TOPICS or tag[1] not in DETAILS for tag in self.tags):
            raise ValueError("only allowlisted, user-approved tags can be indexed")

    @property
    def searchable(self) -> bool:
        return self.ready and self.active and self.consent and self.adult_confirmed


class DiscoveryIndex:
    """Cheap synchronous initial count. Real deployment needs a durable index."""

    def __init__(self):
        self._by_id: dict[str, AnonymousCandidate] = {}
        self._eligible: set[str] = set()
        self._postings: dict[tuple[str, str], set[str]] = defaultdict(set)

    def upsert(self, candidate: AnonymousCandidate):
        if not isinstance(candidate, AnonymousCandidate):
            raise TypeError("candidate required")
        old = self._by_id.get(candidate.agent_id)
        if old is not None:
            self._eligible.discard(old.agent_id)
            for tag in old.tags:
                self._postings[tag].discard(old.agent_id)
        self._by_id[candidate.agent_id] = candidate
        if candidate.searchable:
            self._eligible.add(candidate.agent_id)
            for tag in candidate.tags:
                self._postings[tag].add(candidate.agent_id)

    def search(self, desired_tags: frozenset[tuple[str, str]],
               *, limit: int = 20, exclude: frozenset[str] = frozenset()) -> dict:
        if not isinstance(desired_tags, frozenset) or not isinstance(exclude, frozenset):
            raise ValueError("immutable tags/exclusions required")
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("invalid search limit")
        for topic, detail in desired_tags:
            if topic not in TOPICS or detail not in DETAILS:
                raise ValueError("invalid category")
        found = (set().union(*(self._postings[tag] for tag in desired_tags))
                 if desired_tags else set(self._eligible))
        found.difference_update(exclude)
        # Only a small top-k materialization; no LLM, photos or raw profiles.
        ranked = heapq.nsmallest(
            limit, found,
            key=lambda agent_id: (-len(self._by_id[agent_id].tags & desired_tags),
                                  agent_id))
        return {
            "schema": "bean.agent_relay.discovery.v1",
            "registered_agents": len(self._by_id),
            "eligible_opted_in_agents_worldwide": len(self._eligible),
            "preliminary_candidates": len(found),
            "shortlist": [{"agent_id": agent_id,
                           "categorical_overlap": len(
                               self._by_id[agent_id].tags & desired_tags)}
                          for agent_id in ranked],
            "deep_agent_conversations_completed": 0,
            "verified_romantic_matches": None,
            "calibrated_compatibility_probability": None,
            "count_is_real_world_users": False,
        }


def schedule_followups(*, days_searching: int, scored_candidates: list[dict],
                       max_budget: int = 48) -> dict:
    """Allocate increasing *probes*, not fabricated compatibility gains.

    At least a quarter of capacity explores uncertain candidates. Remaining
    probes concentrate on strong candidates, including revisits after agents
    obtain new information. Caller still owns inter-agent contact permission.
    """
    if type(days_searching) is not int or days_searching < 0:
        raise ValueError("days searching must be nonnegative")
    if type(max_budget) is not int or not 1 <= max_budget <= 200:
        raise ValueError("invalid budget cap")
    if not isinstance(scored_candidates, list):
        raise ValueError("candidate score list required")
    budget = min(max_budget, 4 + 2 * (days_searching // 7))
    normalized = []
    ids = set()
    for item in scored_candidates:
        if not isinstance(item, dict) or set(item) != {
                "agent_id", "fit_index", "factor_coverage_pct", "conversations"}:
            raise ValueError("exact candidate planning schema required")
        ident = item["agent_id"]
        if not isinstance(ident, str) or not ident.isascii() or not 1 <= len(ident) <= 64 or ident in ids:
            raise ValueError("unique anonymous agent id required")
        ids.add(ident)
        fit, cov, n = item["fit_index"], item["factor_coverage_pct"], item["conversations"]
        if (type(fit) not in (int, float) or type(cov) not in (int, float)
                or not math.isfinite(fit) or not math.isfinite(cov)
                or not 0 <= fit <= 100 or not 0 <= cov <= 100
                or type(n) is not int or not 0 <= n <= 100000):
            raise ValueError("invalid candidate score/coverage")
        normalized.append(dict(item))
    # High-fit revisits and uncertainty exploration receive independent slots.
    top_slots = max(1, math.ceil(budget * .75))
    strong = sorted(normalized, key=lambda x: (-x["fit_index"], x["conversations"], x["agent_id"]))
    uncertain = sorted(normalized, key=lambda x: (x["factor_coverage_pct"], x["conversations"], x["agent_id"]))
    chosen = strong[:top_slots]
    used = {x["agent_id"] for x in chosen}
    chosen.extend(x for x in uncertain if x["agent_id"] not in used)
    chosen = chosen[:budget]
    return {
        "schema": "bean.agent_relay.scan_plan.v1",
        "days_searching": days_searching,
        "probe_budget": budget,
        "candidate_count": len(normalized),
        "planned_probes": [
            {"agent_id": item["agent_id"], "action": "repeat_interview"
             if item["conversations"] > 0 else "first_interview"}
            for item in chosen
        ],
        "actual_model_calls": 0,
        "contacts_sent": 0,
        "human_outcomes_verified": False,
    }
