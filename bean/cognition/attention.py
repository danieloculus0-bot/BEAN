"""Attention windows select events for processing without claiming emotion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .significance import SignificanceScorer, SignificanceScore


@dataclass
class AttentionEntry:
    event: dict
    score: SignificanceScore
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"event": self.event, "score": self.score.to_dict(), "reasons": self.reasons}


@dataclass
class AttentionWindow:
    entries: list[AttentionEntry]
    threshold: float

    def top(self, n: int = 10) -> list[AttentionEntry]:
        return sorted(self.entries, key=lambda e: e.score.score, reverse=True)[:n]

    def event_ids(self) -> list[int]:
        return [e.event.get("id") for e in self.entries if e.event.get("id") is not None]

    def to_dict(self) -> dict:
        return {"threshold": self.threshold, "entries": [e.to_dict() for e in self.entries]}


class AttentionFilter:
    def __init__(self, scorer: Optional[SignificanceScorer] = None, threshold: float = 0.5):
        self.scorer = scorer or SignificanceScorer()
        self.threshold = threshold

    def build_window(self, events: list[dict], open_questions: Optional[list[dict]] = None, n: int = 20) -> AttentionWindow:
        entries: list[AttentionEntry] = []
        question_terms = self._extract_question_keywords(open_questions or [])
        for event in events:
            score = self.scorer.score_event(event)
            reasons = list(score.reasons)
            text = f"{event.get('summary','')} {event.get('subtype','')}".lower()
            if any(term in text for term in question_terms):
                score.score = min(1.0, score.score + 0.15)
                reasons.append("open_question_match=+0.15")
            if score.score >= self.threshold:
                entries.append(AttentionEntry(event, score, reasons))
        return AttentionWindow(sorted(entries, key=lambda e: e.score.score, reverse=True)[:n], self.threshold)

    def _extract_question_keywords(self, questions: list[dict]) -> list[str]:
        terms = []
        for q in questions:
            for word in str(q.get("question", "")).lower().replace("?", "").split():
                if len(word) >= 6:
                    terms.append(word)
        return terms
