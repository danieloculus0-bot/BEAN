# Preregistered annealed continuation potential: independent seeds 62–64 (2026-10-12)

**STATUS: UNRUN AT PREREGISTRATION.** This protocol is fixed before opening any 62–64 holdout. Research-only stacked branch from frozen source head `e4fbc725466f8fa6ebcd28e13e599c515a4f254e` (PR #117); original fixed-potential learner blobs: `evolve.py` 6b442cca54e6d5c080af959e5bbd87fd274b8d97, `sponge_dqn.py` 769da37ac2e13566ddc0d83c770d7323cbfc0da7, `test_evolve.py` 2841b1840ea8ce6df67fc3c9441c3dd6f14b77fe. Seeds 41–61 have been seen; 62, 63, 64 are fresh, assigned in advance, with no substitutions or selective stopping.

## Prior evidence and falsifiable hypothesis

Frozen fixed-potential seeds 59–61: evolved minus uninterrupted DQN +0.875, -8.100, +0.200 bricks/game; independent-seed n=3 mean -2.34167, sample SD 4.99827, t95 CI [-14.75806,+10.07473]. Cumulative frozen 53–61 n=9 mean +0.76018, SD 5.49738, t95 CI [-3.46548,+4.98584]. A large negative-transfer outlier remains. We hypothesize that **annealing the existing potential-shaped reward to raw reward during champion continuation** may reduce negative transfer relative to the frozen constant-shaping learner. This is exploratory, not a guaranteed improvement.

## Exactly one bounded learner modification

Preserve **all candidate-search training** unchanged: potential Phi(state) = -0.75 * abs(paddle_bin-7)/7 when the ball descends, zero otherwise; r' = r + gamma*Phi(next) - Phi(current), terminal Phi = 0. Preserve DQN architecture, optimizer, candidate mutation, initializations, exploration, seed multiset, evaluation, gate and training budgets.

**Only the 360 post-selection champion continuation games change:** at zero-indexed continuation episode k, set fixed episode scale s(k) = 1 - k/359 (first 1.0, last 0.0), and use reward r + s(k) * [gamma*Phi(next) - Phi(current)]. The potential scale is constant *within* each episode. This anneals the existing shaping signal to the ordinary reward; it is not a new network, a new source of observations, or a change to scoring. For a one-game continuation, scale is zero. Frozen arm uses the original source unmodified.

## Arms, seeds and sealed evaluation

For each seed 62, 63, 64, execute **two distinct evolved learners** under the same deterministic environment seed multiset: A = annealed continuation on this branch; B = frozen constant-potential continuation by checking out exact commit `e4fbc725466f8fa6ebcd28e13e599c515a4f254e`. Each run also trains its own unchanged uninterrupted DQN control and cold control. Confirm the two DQN control holdout outcomes match exactly for each seed; mismatch is a reproducibility failure and blocks claims. This paired frozen arm prevents attributing unrelated seed effects to the annealing change.

Each arm: population 3 x generations 3 x 30 games = **270 candidate-search games** plus **360 selected champion continuation games**. Its uninterrupted DQN control receives **630 games** from the same environment-seed multiset, with no shaping. Training frames and gradient updates are measured and reported separately, **not equalized**. Candidate selection uses the worst of two disjoint 60-game validation cohorts. Preholdout gate reuses these same validation cohorts (not selection-independent) and accepts evolved only if on BOTH cohorts bricks gain >= +0.25 and survival delta >= -0.05. All arms then score **120 previously unopened paired holdout games** per evolved, uninterrupted DQN, cold and adopted policy. The 62–64 holdout seed ranges are 142000–142119, 143000–143119, 144000–144119. No holdout peeking, tuning, retrying to get a positive result or dropping a failed seed.

**Primary outcome:** seed-level paired difference [annealed evolved bricks/game minus frozen evolved bricks/game], n=3 mean, sample SD and Student-t 95% CI. **Secondary:** raw evolved minus uninterrupted DQN for both arms, gated adopted gains for both, per-seed survival deltas, gate acceptance/rejection, cumulative historical descriptive context. Show all raw negative results, including a failed gate. Do not treat the 120 games per seed as independent learner replicates. Any positive effect is provisional and needs new unseen independent seeds, independent engineering review, and additional environments before public claims or Main merge.

## Execution and integrity gates

Run Python 3.12 focused unit tests and bounded smoke on **both Windows and Linux first**; only if both pass run the 62–64 frozen/annealed matrix. Save `results.json`, `final-evolved-weights.json`, `evolution.sqlite` for every seed and arm; verify SQLite integrity, nine-entry SHA256 chain and tip, actual final-weight fingerprint, artifact ZIP digests, game/frame/update budgets, source SHA and learner blobs. Do not change code or preregistration while trials run. This is engineered-state Breakout, not pixel Atari or AGI. No Main merge, live trading, or hardware control.
