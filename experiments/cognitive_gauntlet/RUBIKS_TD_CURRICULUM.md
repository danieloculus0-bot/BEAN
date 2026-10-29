# Validation-directed BEAN cube learning

This experimental module reuses BEAN SpongeTD, legal cube transitions,
24-orientation canonicalization, and the existing frozen learned-value
controller. It does not invoke cubejs or a conventional solver for training,
inference or benchmark scoring.

The two arms start with identical self-play and learned Q-values. Failures
on a disjoint validation cohort choose the depth of additional legal
self-play for the candidate. The unchanged baseline instead replays its
original transitions. Both receive exactly the same number of extra TD
updates, but different experience diversity and collection costs.

The independent holdout excludes every rotation-equivalent state from
either training graph, validation and other holdout cases. Original scrambles,
both move sequences, failed attempts, excluded states, Q digests, seeds,
training episodes and validation decisions are preserved in the JSON receipt.
Neither policy is told the inverse scramble. The training exploration depth
ceiling is NOT a maximum solution-move limit. Optimality is not proven.

Run:
    python -m unittest bean.tests.test_cognitive_rubiks_curriculum -v
    python -m experiments.cognitive_gauntlet.rubiks3_curriculum

A full-length 20-turn BEAN-native solution remains an explicit unproven
milestone. This is experimental policy learning, not Core deployment.
