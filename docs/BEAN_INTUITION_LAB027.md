# BEAN Lab027: Learned intuition and episodic escape

**Branch:** experiment/bean-intuition-maze-20261021  
**Status:** actual BEAN native SpongeTD research experiment; NOT production, NOT generalized intelligence evidence.

## Why this experiment exists

BEAN's earlier SpongeTD and SpongeDQN experiments were tied to a three-action
Breakout environment. The *SpongeTD Q engine* was already abstract: it accepts
arbitrary JSON-serializable state and named actions. This experiment copies the
unaltered source files from the earlier SpongeTD branch and builds a reusable,
domain-neutral \`SpongeIntuition\` selector over those existing learned Q-values.

The new selector exposes optional legal actions and expected destination refs
provided by the host task. It scores learned action preferences while discounting
repeated local choices and recently visited destinations. No learned policy
values are changed by evaluation. The memory resets each episode; the durable
Q table is checkpointed with BEAN's original SHA-verified compressed Journal.

## Actual learning experiment

BEAN trains via its existing \`SpongeTD.learn\` one-step TD updates on
**3,000 procedural 5..8-cell grid puzzles**. Each puzzle has walls, a key,
and an exit accessible only after collecting the key. Q inputs include
goal-relative coordinates, goal-distance bucket, nearby wall flags, and key
status, enabling feature reuse between unseen map layouts.

A separate 180-map **validation** split selects the episodic loop-breaking
parameters using ONLY validation outcomes (18 candidate combinations).
Once selected, the configuration and Q-values are frozen. A fresh 240-map
**holdout** split measures:

1. Cold, untrained Q policy with no loop-breaking bonuses.
2. Trained SpongeTD Q policy with no loop-breaking bonuses.
3. Cold Q policy WITH the selected loop-breaking.
4. Trained Q policy WITH the exact same loop-breaking.

The third control matters: a strong exploration heuristic can solve maps without
learned Q-values. Efficiency differences between arms 3 and 4 are more informative
than success alone. Reward shaping provides target-distance information; it is
reported explicitly, not confused with unguided intelligence.

Every train, validation and holdout episode is recorded in a deterministic,
lossless \`events.jsonl.gz\` ledger, with individual seed, arm, outcome and
step counts; \`scoreboard.json\` records SHA256 hashes for seed splits, the
full event ledger, selected policy, checkpoint, bootstrap estimate and caveats.
The original Q codec and Journal verify restart recovery.

## Run with existing BEAN

\`\`\`bash
python -m unittest bean.tests.test_intuition_maze -v
python -m bean.optimization.intuition_maze --training 3000 --validation 180 --holdout 240 --output lab027-results
\`\`\`

Run under an experimental worktree/branch. No real-world action endpoints,
hidden model inference, code patching, safety-policy changes, or autonomous
production rollout are added. The new controller is usable by future tasks
with any BEAN SpongeTD compatible action/state interface; the current evidence
is limited to this **single synthetic puzzle family**.

The validation dataset and holdout dataset are deterministically generated
from separate, nonoverlapping seed ranges. Deterministic generation is a
reproducibility choice, not third-party independent blindness. Exact source,
full event history and a held-out evaluator are essential before making
comparisons outside this puzzle family.

## Independent reproducibility

The dedicated CI on Windows and Ubuntu executes the actual original SpongeTD
class, tests the original BEAN Core regression, runs all 3,000 episodes, and
uploads the event log plus scoreboard as inspectable build artifacts. Compare
the two platform summaries and source SHAs; repeat runs should match if the
algorithm and dependencies have not changed. A successful CI run shows
*mechanism correctness*, not broad problem-solving ability.
