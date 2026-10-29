# BEAN-native joint-goal rescue pilot

**Status: experimental, not a full Rubik's Cube solver.**

The preceding pure joint-cubie SpongeTD controller often paused while
wandering through unseen full-cube states, and performed worse than the
unchanged full-state controller. This experiment asks a narrower question:
can BEAN retain its successful full-state learned decisions and use a
separately learned 96-pair controller only when the full-state policy has
no positive learned action?

## What BEAN does

The primary controller is the unchanged two-transition BEAN SpongeTD
learned-value rollout. It selects its own moves from legal cube state
transitions and frozen Q values. When that controller would stop for lack
of a positive learned action, the candidate may instead select a legal
action using the separately trained corner-edge joint Q table. On the
next state it tries the full-state policy again.

The candidate never receives an inverse scramble, cubejs answer,
conventional search result, or demonstration. It is not a general
search wrapper. The joint-Q learner uses the same legal self-play graph
and pair-completion rewards as the existing joint-cubie experiment.

An unchanged initial full-state policy is retained as a diagnostic
control. A second, stronger full-state control receives additional
ordinary TD replay equal to the **total number of TD updates** in the
candidate's full-state plus joint-Q learners. The two arms do not have
matched representation size, inference cost, or reward information.
No peer framework runtime is involved.

## Honest evaluation

New, disjoint holdout seeds are 26000 to 26009 and 27000 to 27009,
with scramble lengths 3, 4, 5, 6, and 20. Training uses seeds 0 to 15
and lengths 2 to 6. Rotation-equivalent training overlaps and repeated
holdout states are excluded with original case receipts preserved.

Each record includes the original evaluator-only scramble, full legal
state, initial control moves, matched-budget control moves, candidate
moves, each failure reason, full-state versus joint-rescue action counts,
Q digests, source revision, exclusions, and independent replay results.
The candidate must exactly preserve a successful initial controller
route; this is a safety property, not evidence of novel learning.
A rescue success beyond both controls would be stronger evidence.

An invocation uses a **128-action compute slice**, not a total solution
move limit. Unfinished cases are marked paused, never solved or
definitively failed. The checkpoint stores the entire legal route,
starting state, action-source counts and hashes of both frozen Q tables;
resuming with different Q tables is rejected. Later invocations can
continue with `policy_solve_joint_rescue(..., checkpoint=receipt)`.
The benchmark currently evaluates one slice and retains all paused
checkpoints. It does not claim shortest half-turn-metric solutions.

Run:

    python -m unittest bean.tests.test_cognitive_rubiks_joint_rescue -v
    python -m experiments.cognitive_gauntlet.rubiks3_joint_rescue --test-seed-start 26000 --output cognitive-gauntlet-results/rubiks3-rescue-26000.json
    python -m experiments.cognitive_gauntlet.rubiks3_joint_rescue --test-seed-start 27000 --output cognitive-gauntlet-results/rubiks3-rescue-27000.json

Cross-platform CI archives complete JSON cases, failures, pauses, and
exclusions. **Do not claim improvement before exact-revision CI and
independent replay evidence.** The 20-turn BEAN-native solving
notification threshold remains unmet until a full unseen legal cube is
actually solved and verified without external solver inference.
