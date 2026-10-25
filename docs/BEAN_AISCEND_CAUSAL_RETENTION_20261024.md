# Domain-capable DQN and retained AIscend learning

BEAN CONTEXT ACK v1

Task: wire the real BEAN learners into a chronological portfolio simulation and verify retained learning after restart.

Existing systems checked: hosted BEAN status and older recall; Core main `79955cf776526b6bd71c060deee926b5d6a49b35`; native reasoning skills `378d8ba`; original neural DQN `2eb05f655cbefce888fc38316a24cfb52b571deb`; AIscend atlas `a8cea61`; Bridge `a4f5ebe`.

Confirmed assets reused: SpongeTD, LearningRuntime, measured feedback, SpongeIntuition, SpongeDQN's original replay/target-network/Huber-loss/Adam engine, SHA-chained SQLite Journal and compressed Sponge codec. Hosted notes are not a neural trainer.

Ledger/scoreboard reviewed: anticipatory-ledger and Lab009 scoreboards. They show repeatability and limited retained evidence, not profitable trading or general neural learning.

Current evidence: main Core regressions and atlas/Bridge contracts passed at their recorded revisions; source-author workflows have failures. New domain-DQN tests demonstrate actual gradient updates and exact continuation after restoration, not economic success.

Unknowns/conflicts: the original DQN accepts three engineered Breakout numbers. The original bulk price archive contains short/stale price series despite extensive other metrics. The companion experiment supplements it with current API historical prices/volume. These remain current-vintage reference values, not executable exchange fills or point-in-time news.

Minimum change: port the existing experimental DQN into a branch of current Core, support explicit input dimensions and named actions, retain complete training state, and make frozen TD choice non-mutating. The portfolio environment remains in AIscend.

Runtime/behavior-policy changes: optional research learner only. No financial execution authority, hosted memory training, inference filtering or new approval requirement.

## Implementation

`bean.optimization.sponge_dqn.SpongeDQN` preserves the original `3-64-64-3` default encoder and DQN update. Explicit `observation_size`, `actions` and `domain` allow the existing network machinery to consume a documented market observation. The update uses the original replay sampling, target-network values, Huber loss, Adam and gradient clipping. PyTorch is optional.

A scored checkpoint now files online weights, target weights, Adam state, replay, Python RNG, update counters, configuration and source/evaluation metadata through the existing compressed codec and SHA journal. Restore checks hashes and dimensions. A retained negative trial is not automatically promoted. Tests verify identical subsequent choices and the same next gradient update after a process restart.

`SpongeTD.choose` previously inserted zero Q entries while reading unseen states. It now reads a default without altering the table, so frozen-policy checksums remain stable. Reward updates continue through `learn`.

## Verify

```bash
python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
python -m unittest bean.tests.test_dqn_domain_retention bean.tests.test_learning_runtime bean.tests.test_measured_feedback -v
```

The companion AIscend experiment isolates policy inputs from the market-history process, locks strategy selection using development/validation results, then evaluates frozen and causally updating policies with matched controls. Outcome records, failed runs and retained checkpoints are part of the experiment archive. A software test or a retained checkpoint alone is not evidence of profitable trading.

READY FOR REVIEW: optional learner interface and retention mechanics are implemented; economic results belong to the separately recorded AIscend experiment.
