# BEAN learned cubie subgoals: separate test of representation

Status: **experimental; no general 3x3 solving claim**. This experiment follows
the negative hotter/colder result, which tied terminal-only SpongeTD 36/94 on
fresh short/long heldouts and solved 0/20 twenty-turn puzzles.

## Hypothesis

The earlier SpongeTD Q table memorizes whole-cube states. Even perfect
reward shaping cannot transfer a Q entry to a genuinely new whole-cube state.
Test a *different representation*, not another reward replay scheduler:
BEAN's existing SpongeTD learns 20 independently identifiable cubie
subgoals, each represented by one of 24 position/orientation states. At
inference it aggregates learned action values for all 20 cubies into one
legal face turn. This is an actual learned action controller, not a conventional
full-cube search wrapper.

Training uses **only observed legal full-cube self-play transitions**, no
reference solver, inverse scramble, precomputed solution route, or test
outcome. Local rewards encourage newly solved pieces (+1), penalize
destroying solved pieces (-0.2), reward hotter local transitions (+0.05),
penalize colder (-0.05), and penalize neutral unsolved moves (-0.01).
Already solved pieces staying solved earn zero. These are heuristic *local*
subgoal rewards, not a proof of progress toward a globally shortest route.

The unchanged comparator is the previously demonstrated rotation-equivariant
SpongeTD full-state learner with two-transition learned-value controller.
Both arms use the same observed self-play source and **the same number of
SpongeTD.learn updates**. The baseline gets extra seeded replay to match
the candidate's 20 per-cubie updates per full-state transition. The arms
receive different reward labels and representations, so matched update
counts do not imply equal information content or equal CPU costs.

## Independent evaluation

Training seeds: 0 to 19, lengths 2 through 6, three epochs.
Predeclared independent holdouts: seeds 18000 to 18009 and 19000 to 19009,
lengths 3, 4, 5, 6 and 20. Canonicalize under the 24 proper cube rotations
to exclude training-state overlaps and duplicate holdouts. Every original
scramble is retained as **evaluator-only** evidence. Inference sees only
the legal scrambled facelets and the frozen learned Q table.

No arbitrary solution-move ceiling. The policy stops on a repeated state
or lack of learned preference, and the evaluator independently replays
every produced move sequence to verify solved state. This is not a
complete/resumable general search and cannot establish shortest HTM.
Full 20-turn successes and failures must be reported separately.

Reproduce:

    python -m unittest bean.tests.test_cognitive_rubiks_pieces -v
    python -m experiments.cognitive_gauntlet.rubiks3_pieces --test-seed-start 18000 --output cognitive-gauntlet-results/rubiks3-pieces-18000.json
    python -m experiments.cognitive_gauntlet.rubiks3_pieces --test-seed-start 19000 --output cognitive-gauntlet-results/rubiks3-pieces-19000.json

Each JSON receipt preserves source revision, training episodes, frozen
policy hashes, matched TD update counts, original scramble, legal starting
state, candidate/baseline move sequences and counts, failures, overlap
exclusions, piece-feature coverage, and independently replayed success.
All four Linux/Windows Python 3.11/3.12 jobs archive all receipts.

## Interpretation gate

This is a *piece-factorized learning microbenchmark*, not a head-to-head
against OpenNARS, Hyperon, PLN, Voyager, Letta, or DreamerV3. No external
runtime executes. Independent cubie subgoals can compete: locally improving
one piece can break another. A full-cube success, if any, must be attributed
to this BEAN-native learned controller only after independent unseen-state
replay, with exact commit, failures, move counts and comparison to the
unchanged baseline. Without such evidence, the user's full-cube notification
condition is **not met**. No production cognition or mainline files change.

## First untouched holdout result (2026-10-29)

At commit `d2a4c2c80f09c2a58b49e887545bb691b645fe4f`, all four isolated
piece-subgoal CI jobs passed on Linux/Windows, Python 3.11/3.12:
https://github.com/danieloculus0-bot/BEAN/actions/runs/40881337272

- Cohort 18000: 40 eligible, 10 excluded; unchanged baseline **7 solved**,
  learned independent-cubie controller **0 solved**; 7 reverse regressions,
  0/10 twenty-turn successes.
- Cohort 19000: 48 eligible, 2 excluded; unchanged baseline **10 solved**,
  learned independent-cubie controller **0 solved**; 10 reverse regressions,
  0/10 twenty-turn successes.
- Combined: **0/88 versus 17/88** unchanged baseline, 17 regressions,
  zero gains, and **0/20** twenty-turn successes.

This is an explicit **negative** result. The individual cubie value
representation did not produce coordinated full-cube decisions, even with
the same number of SpongeTD updates. Preserve the candidate and all failed
case receipts rather than promoting it as progress. The next hypothesis
must learn *interactions between subgoals* or a global goal-conditioned
value, rather than summing independent piece preferences.

The first run also exposed a cross-platform source-receipt mismatch:
Windows checked-out source bytes use different line endings than Linux.
Commit `cb40acbc4a0cb214aeb5d2069b215b39b936ed32` normalizes the
module source hash to UTF-8 text before hashing. The prior original
receipts and negative results remain intact. Do not treat this portability
fix as improved cube-solving ability; verify the new exact-head CI separately.
