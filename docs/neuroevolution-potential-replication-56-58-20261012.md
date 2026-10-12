# Independent replication: frozen potential-shaped neuroevolution (56–58)

**Preregistered 2026-10-12, before opening the fresh holdout.** Research-only; no claims of proven improvement.

## Reason for replication

PR #113 / GitHub Actions run [38259342694](https://github.com/danieloculus0-bot/BEAN/actions/runs/38259342694) found raw evolved-minus-uninterrupted DQN holdout differences on training seeds 53,54,55 of **+3.40000, -5.80834, +6.85000 bricks/game**; two of three gates accepted, one rejected. Mean **+1.48055**. This is a potentially interesting *but inconsistent* result with substantial uncertainty; prior holdouts 41–55 are contaminated for future selection and are not fresh tests.

The follow-up deliberately changes **zero learner parameters or selection/gating logic**. It inherits the research code at source SHA `cf6ecb3775b0401130a1aa0af898b96871654c78` on PR #113. The specific source file content hashes (Git blobs) at preregistration are: `experiments/sponge_breakout/evolve.py` = `6b442cca54e6d5c080af959e5bbd87fd274b8d97`, `experiments/sponge_breakout/test_evolve.py` = `2841b1840ea8ce6df67fc3c9441c3dd6f14b77fe`, and `bean/optimization/sponge_dqn.py` = `769da37ac2e13566ddc0d83c770d7323cbfc0da7`. All previous positive/negative results and immutable archive receipts remain on their original branches and Actions artifacts.

## Frozen algorithm / fair comparisons

- Evolved training ONLY: `Phi(s) = -0.75 * abs(state[0]-7)/7` when descending, otherwise zero; shaped learning reward `r' = r + gamma*Phi(next) - Phi(current)`, terminal `Phi = 0`. No game-scoring or observation changes. Ordinary DQN remains raw-reward trained.
- Full inherited learner state and exactly `3 generations × 3 candidates × 30 episodes = 270` search episodes plus `360` post-selection champion continuation episodes. Uninterrupted DQN receives the exact same **630 episode seed multiset**, trained continuously.
- **Fresh, sealed training-seed replicates: 56, 57, 58**. No substitutions, no stopping after favorable outcomes and no selection from this cohort.
- Candidate selection/fitness: worst of two 60-game validation cohorts. The same cohorts also implement the pre-holdout gate, which is **not selection-independent**. The gate accepts evolution only if BOTH cohorts exceed ordinary DQN by at least +0.25 bricks/game while survival decreases by no more than 0.05 each.
- After frozen gate decision, evaluate evolved, ordinary uninterrupted DQN and original cold control on the SAME **120 newly sealed holdout games** per replicate. Do not repeat/tune on these holdout seeds.
- Compare raw evolved-minus-DQN outcome (all replicates), as well as gated adopted-policy outcome; record cold control, survival, candidate/lineage and control games, frames, gradient updates, final trained-policy SHA-256, results.json SHA-256, journal chain tip and code SHA.
- Training episode budgets are matched across total evolutionary population versus control; **selected lineage frames, updates and actual experiences are not matched**. No claim of a frame-matched controlled test. With 3 replicates, variance and uncertainty may be too wide for a firm conclusion.

## Execution and decision rule

Run Python 3.12 focused DQN/SQLite and new shaping regression tests on **both Windows and Linux first**. Only if those pass, start 56–58 as matrix jobs. Upload artifacts even for negative experiments. Report raw paired means, standard deviation and uncertainty with explicit n=3; do not assert independent replicated gains based on passing unit tests, gate acceptances or pooled per-game scores treated as independent training replicates.

If results are positive or mixed, preregister a **different unused seed cohort** to assess replication again and seek engineering review before promoting or merging any learner. If the result is negative, record it unchanged and develop at most one bounded new hypothesis with separate fresh held-out seeds. Never merge to Main or operate wallets/hardware in this research workflow.
