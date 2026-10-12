# Preregistration: raw-reward champion continuation, seeds 65–67 (2026-10-12)

**STATUS AT REGISTRATION: UNRUN.** Research-only. This branch starts from the previously observed annealed source commit `03cae7a4cd22cc4d1baa318d5b41a02b3fcb0316`; original frozen source was `e4fbc725466f8fa6ebcd28e13e599c515a4f254e`. Seeds 41–64 are observed. Seeds 65, 66, 67 are provisionally allocated as fresh independent learner seeds, with no substitutions, early stopping, or exclusions for poor results. If prior use is discovered, stop before any holdout, document it, and preregister genuinely unused replacements rather than silently substituting.

## Question and single bounded change

Previous annealed-minus-frozen evolved differences on seeds 62–64 were +7.56666, +10.45833, -3.36666 bricks/game (n=3; mean +4.88611; Student-t 95% CI includes zero). The 12 observed frozen seeds 53–64 were mixed (7 positive, 5 negative vs DQN), and these observations do not establish superiority. Hypothesis: **using only raw environmental reward throughout all 360 selected-champion continuation games** may reduce negative transfer relative to the already-tested linearly annealed continuation.

Change only the selected champion's continuation reward schedule: `shaping_scale=0.0` for every continuation episode, instead of annealed `1 - episode/359`. Preserve the potential-shaped 270 candidate-search games exactly, network, optimizer, inherited learner state, exploration, seed multiset, candidate selection, controls, adoption gate, and all budgets. The ordinary uninterrupted DQN remains raw-reward-only. No holdout feedback influences training.

## Frozen evaluation protocol

For each of the independent seeds **65, 66, 67**, compare A = new raw-only continuation (this branch) with B = annealed continuation checked out from exact source commit `03cae7a4cd22cc4d1baa318d5b41a02b3fcb0316`. Each arm trains a separate unchanged 630-game uninterrupted DQN and evaluates the cold learner. DQN results must match exactly within seed across arms, or the pair fails reproducibility and no positive claim is made.

Each arm: 3 generations × 3 candidates × 30 games = 270 search training games; 360 selected-champion continuation games; 630 uninterrupted DQN games on the same environment seed multiset. Frames and gradient updates are recorded separately and **not equalized**. Two disjoint 60-game validation cohorts are used for candidate selection and reused for preholdout promotion; gate accepts evolved only if **both** cohorts show at least +0.25 bricks/game and at most -0.05 survival delta versus DQN. Holdout: **120 paired, previously unopened games** for evolved, DQN, and cold per seed and arm; adopted policy is the gated choice. Fixed holdout ranges: seed 65 = 145000–145119; 66 = 146000–146119; 67 = 147000–147119. Do not open them before both OS gates pass. Do not tune or rerun after viewing them.

Primary outcome: paired seed-level raw-only evolved minus annealed evolved bricks/game, with every seed reported, sample mean, sample SD, Student-t 95% CI (n=3, wide). Secondary: raw evolved minus uninterrupted DQN, gated adopted minus DQN, survival, gate decisions, training frames and updates, and cold comparisons for both arms. Preserve all negative evidence. Treat learner seeds, not the 120 games within each seed, as independent replicates. Any gain requires genuinely unused further seeds, independent engineering review, and new environments before public claims or Main merge.

## Execution and evidence integrity

Before any fresh seed runs: Python 3.12 focused neural unit tests and bounded smoke using previously observed seed 41 on **Windows and Linux**. Only when both pass, run the fixed 65–67 paired-arm matrix. Save every arm's `results.json`, `final-evolved-weights.json`, and `evolution.sqlite`, including failures; inspect actual job logs, source SHAs and Git blobs, result and model SHA256, SQLite integrity and chained journal tip, per-arm game/frame/update budgets. Never merge Main, trade live money, or control hardware. No adaptive seed replacement, no cherry-picked claims. Engineered-state Breakout is not pixel Atari or general intelligence.
