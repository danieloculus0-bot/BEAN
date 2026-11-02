"""Preserve explicit corrections of misunderstood intent in reasoning context.

No hard-coded reading of a disputed statement, no fabricated earlier dialogue,
and no policy restricting BEAN's experimental inference.
"""
from __future__ import annotations

import re


_CORRECTION_PATTERNS = (
    re.compile(r"\b(?:you|u)\s+(?:do\s+not|don't|did\s+not|didn't)\s+(?:even\s+)?(?:get|understand|hear)\s+me\b", re.I),
    re.compile(r"\b(?:that's|that is)\s+not\s+what\s+i\s+(?:meant|said)\b", re.I),
    re.compile(r"\byou(?:'re| are)\s+missing\s+(?:my|the)\s+point\b", re.I),
)

_CORRECTION_GUIDANCE = (
    "USER INTERPRETATION CORRECTION: The user has challenged a previous "
    "interpretation. That earlier paraphrase is not verified. Preserve the "
    "original utterance separately from your guesses about its meaning. "
    "If the earlier words are absent from the supplied evidence, acknowledge "
    "that they are missing; ask one precise clarification rather than invent "
    "a confident explanation. Do not portray your interpretation as the "
    "user's confirmed meaning. This does not replace the current query.\n"
)


def has_interpretation_correction(query: str) -> bool:
    """Recognize explicit corrective feedback, independent of its topic."""
    return isinstance(query, str) and any(p.search(query) for p in _CORRECTION_PATTERNS)


def context_for_interpretation(query: str, context: str) -> str:
    """Preserve source-linked context unchanged unless the user corrects it."""
    if not has_interpretation_correction(query):
        return context
    return _CORRECTION_GUIDANCE + context
