# BEAN Double DQN Research 50-52

Status: preregistered, untested, research-only.

Prior independent raw evolved versus uninterrupted DQN holdout differences: seeds 44-46 = -4.85000, +0.23333, +1.90000; seeds 47-49 = -6.36666, -0.40834, -0.55000 bricks/game. No replicated gain. All six seeds are seen. Previous artifacts and hashes remain in Actions runs 38229337741 and 38247985900.

Single new hypothesis: Double DQN target selection (online network argmax; target network evaluation) reduces maximization bias. Apply it equally to evolved candidates and uninterrupted control. Preserve all other existing learner-state and promotion-gate logic.

Unseen training seeds 50, 51, 52; two disjoint validation cohorts of 60 games each, holdout 120 games. Per seed: 3 candidates x 3 generations x 70 training games = 630 candidate games; control gets 630 games. Report actual frames and updates separately. The pre-holdout gate requires +0.25 bricks and no worse than -0.05 survival on both cohorts. Compare raw paired evolved versus uninterrupted Double DQN and post-gate adopted policy; preserve all losses, survival, SHA-256 source/results/capsules, journal receipts. Never retune on opened holdouts.

No Main merge without independent review. No live trading or hardware control.
