# BEAN neural learner: fixed-budget champion continuation (research preregistration)

Status as of code commit `bf93aa45abc3cbb61e8b0b4eb16436bbe21a9c96`: **unexecuted hypothesis, no demonstrated learning gain**.

## Motivation and prior failures

The earlier full learner-state inheritance trial [PR #110](https://github.com/danieloculus0-bot/BEAN/pull/110), run 38247985900, on independent seeds 47,48,49 returned -6.36666, -0.40834, -0.55000 evolved-vs-uninterrupted-DQN bricks/game (mean -2.44167, 0/3 gains). All were rejected by the unchanged pre-holdout gate. Raw receipts and SHA hashes are archived in `docs/neuroevolution-learner-state-47-49-20261012.md`. Those holdouts and all previous 41–46 seeds are seen; **never optimize against them**.

The leading testable hypothesis is resource allocation: a selected neural lineage saw only 18,923–32,643 frames while an uninterrupted DQN saw 156,218–254,667 on the same total game count. This is an association, not proven causation.

## Single bounded change

Reallocate the existing **630 total training episodes** per training seed: **270 search episodes** (3 generations × 3 candidates × 30 games each), followed by **360 episodes of continued training for the selected champion**. Continue the same policy using the full inherited learner state, optimizer, replay, RNG, and learning counters. Uninterrupted DQN gets the **identical 630-episode training-seed multiset** (candidate repetitions plus champion-extension seeds) sequentially.

This preserves the same total episode budget rather than increasing neural evolution's compute without acknowledging it. The selected lineage will have between 390 and 450 training episodes; the uninterrupted control has 630. Actual frame and update budgets can still differ considerably and MUST be reported. Training longer on a champion could improve or degrade performance; the outcome is unknown.

The selected lineage weights were scored and journaled *before* continuation. The policy actually evaluated after continuation is separately saved to `final-evolved-weights.json`, its canonical SHA-256 recorded as `final_policy_sha256`, and raw positive/negative outcomes stored in `results.json`; never represent the earlier lineage hash as the final model hash.

## Preregistered unviewed trial

- Fresh training seeds: **50, 51, 52**. No post-hoc substitutions.
- Total training games: 630 search+continuation episodes per training seed, versus uninterrupted DQN trained on 630 episodes of the same multiset. Three independent paired training seeds, not pixel-input Atari.
- Candidate ranking: worst-of-two candidate-validation cohorts as in prior experiment, unchanged.
- Promotion gate before holdout: BOTH disjoint 60-game validation cohorts must have evolved-minus-DQN bricks/game >= +0.25 and evolved-minus-DQN survival >= -0.05. These gate cohorts are also used by candidate selection and are **not selection-independent**; do not claim independent validation.
- Final sealed holdout: 120 games per final policy per training seed, seen for the first time after promotion decision.
- Measure **raw** evolved-minus-DQN, **adopted** gate decision, cold baseline, survival, training frames and updates, checkpoint/journal SHA, and source commit SHA. Report the mean, variance, and uncertainty across the three training seeds, all failures included.
- Windows Python 3.12 and Linux Python 3.12 focused neural/SQLite unit tests and bounded smoke must pass before the large trials.
- Success is not established by one positive holdout or a passing CI job. Request independent review and separate fresh replication seeds before any claim or Main merge.

## Boundaries

Research branch only. Never merge to Main automatically, operate trading wallets or hardware, tune on opened holdouts, invent evidence, or publish claims of achieved learning gains. New experiments require another preregistered hypothesis and different sealed training and holdout seed families.
