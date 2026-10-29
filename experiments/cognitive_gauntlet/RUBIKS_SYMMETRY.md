# BEAN 3x3: rotation-equivariant SpongeTD pilot

Isolated experimental component available on `main`, not wired into BEAN's production cognition runtime. The holdout evaluator is now **v2**, using rotation-equivalence classes rather than exact state strings for holdout independence. This is **BEAN's own trained tabular policy**, not
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

## Paired evaluation and corrected holdout independence (v2)

- Training: deterministic self-play seeds 0 through 249, lengths 2 to 6, 12 epochs of legal-transition reward propagation, with no solver demonstrations.
- Frozen test cohorts: seeds 1000-1009, 2000-2009 and 3000-3009; lengths 3, 4, 5, 6 and 20 (150 predeclared cases).
- The v2 exclusion rule uses the canonical state under all 24 proper cube rotations for **both** training overlap and repeated holdout states. This excludes 33/150, leaving **117 independent rotation classes**. The same eligible cases are scored by both policies, with excluded cases and their reasons retained.
- Unchanged SpongeTD baseline: **6/117** solved. Rotation-equivariant SpongeTD: **32/117** solved, with 26 candidate-only successes and zero reverse regressions in this sample. Untrained rotation-equivariant policy: **0/117**.
- All **30/30** held-out 20-turn scrambles still fail. The learner is not a general cube solver.
- Every candidate success independently replays to the solved cube and matches the separate bounded optimality check for at most six HTM moves.
- Training costs differ: the symmetry-aware learner uses **26,880** TD updates versus **33,024** in the baseline. They share self-play and epochs but not the transition graph. No external AI framework was compared.

**Verified experimental source and CI:** Gauntlet source `aa1457c801c949954f7ee63caf5c2c7075c31cc6`, [GitHub Actions run 40828666437](https://github.com/danieloculus0-bot/BEAN/actions/runs/40828666437), all eight fair-replay/cube-policy jobs successful on Linux/Windows with Python 3.11/3.12. Complete case-level artifact archives were retained by GitHub. The original experimental branch and receipts are untouched.

**Historical v1 result:** The earlier `33/118` candidate versus `6/118` baseline counted one rotation-equivalent holdout state twice. That result is preserved as historical evidence, **not** a comparable independent-case v2 result. The corrected v2 is `32/117` versus `6/117`; the learner's policy and training algorithm were not changed by this correction.

The v2 source and exact regression tests were copied byte-for-byte to `main` from the verified experimental source. A successful experimental-branch CI run does **not** certify the later `main` commit; exact-head mainline CI must be inspected separately.

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
