# BEAN 3x3: rotation-equivariant SpongeTD pilot

The current v2 holdout correction remains on the experimental branch; the original CI-proven v1 policy was separately integrated into `main` at `a74ccfe3`. This is **BEAN's own trained tabular policy**, not
cubejs, an inverse-scramble recipe, a conventional solver, or a claim of
arbitrary full-cube solving. The 3x3 move geometry is the unchanged
`rubiks3.py`; terminal rewards and Q updates use existing mainline `SpongeTD`.

## What changed

`rubiks3_symmetry.py` identifies the 24 proper whole-cube rotations. It
rotates both sticker positions and color names, so the solved cube remains
solved. Every legal move is mapped into the same rotated coordinate frame.
BEAN learns a shared Q table for equivalent cube states, rather than treating
all 24 orientations as unrelated experiences. Its frozen policy chooses a
positive learned action value, or a single model step toward a learned value
on an unseen state. It does not search for a solution or receive the scramble
trace at inference. Failed policy decisions are **not** rescued by a reference
solver. There is no arbitrary solution-move ceiling: the policy stops at the
goal, a cycle, or missing positive learned value.

## Paired evaluation, local Linux Python 3.13

- Training: deterministic self-play seeds 0 through 249, lengths 2 to 6,
  12 epochs of legal-transition reward propagation. No solver demonstrations.
- Frozen test cohorts: seeds 1000-1009, 2000-2009, and 3000-3009;
  lengths 3, 4, 5, 6, and 20 (150 predeclared cases).
- Exclude states equivalent under one of the 24 rotations to a **training**
  state, and repeated **rotation-equivalent holdout** states. Both baseline and
  candidate receive the same 117 eligible states. This stricter v2 rule excluded
  33/150 cases. Canonical state is recorded for every included/excluded case.
- Matched original SpongeTD policy: **6/117** eligible cases solved.
- New rotation-equivariant SpongeTD: **32/117** solved, including 26 cases
  the unchanged policy missed and zero reverse regressions in this sample.
- Untrained rotation-equivariant policy: **0/117**. Every one of the 32
  successes independently replays to the solved cube and matches the shortest
  length proved by the separate bounded search (at most six HTM moves).
- All **30/30** held-out 20-turn scrambles remain unsolved. The candidate is
  **not** a general Rubik's Cube solver. Training costs are not matched:
  the symmetry-aware learner uses a different transition graph and **26,880**
  TD updates versus **33,024** in the unchanged control. The controls are
  matched on self-play and epochs, not on identical transition graphs.

**Evidence:** v2 source at `aa1457c801c949954f7ee63caf5c2c7075c31cc6` passed [8/8 exact-head CI jobs](https://github.com/danieloculus0-bot/BEAN/actions/runs/40828666437) on Linux/Windows, Python 3.11/3.12. Cohorts 1000, 2000 and 3000 contain 36, 41 and 40 eligible cases respectively; all 30 eligible 20-turn cases failed. The prior v1 **33/118** figure is retained as historical evidence from before the stronger holdout deduplication and must not be substituted for v2.

The three cohort receipts record original scrambles (evaluator only), states,
selected moves, every failure, exclusions, training episodes, Q-table digests,
module digest, seed splits, and exact independent replay. `GITHUB_SHA` supplies
the checkout revision on CI; local runs are marked `local_unverified`.

## Reproduce

```bash
python -m unittest bean.tests.test_cognitive_rubiks3 bean.tests.test_cognitive_rubiks_sponge bean.tests.test_cognitive_rubiks_symmetry -v
python -m experiments.cognitive_gauntlet.rubiks3_symmetry --output cognitive-gauntlet-results/rubiks3-symmetry-1000.json --test-seed-start 1000
python -m experiments.cognitive_gauntlet.rubiks3_symmetry --output cognitive-gauntlet-results/rubiks3-symmetry-2000.json --test-seed-start 2000
python -m experiments.cognitive_gauntlet.rubiks3_symmetry --output cognitive-gauntlet-results/rubiks3-symmetry-3000.json --test-seed-start 3000
```

No external AI runtime was compared. This is transfer of learned values through
exact cube symmetry, not proof of general reasoning, and the model is not wired
into BEAN Core or the hosted BEAN connector.
