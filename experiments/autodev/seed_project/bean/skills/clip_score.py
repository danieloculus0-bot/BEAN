"""Seeded source defect that BEAN must discover and rewrite."""

def clip_score(score):
    return max(0, min(score, 100))
