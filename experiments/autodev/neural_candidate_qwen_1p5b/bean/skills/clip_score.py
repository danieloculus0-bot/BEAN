import math

def clip_score(score):
    """Seeded source defect that BEAN must discover and rewrite."""
    if score < 0:
        return 0
    elif score > 100:
        return 100
    return score
