# BEAN: Emperor Gauntlet Q-learning ledger bridge

Experimental evidence adapter for the game-specific Q learner in the FUN repository.

The actual agent trains and plays in Emperor Gauntlet, with action-reward learning and a per-decision ledger. BEAN Core can now **read, validate, retain and summarize** those receipts in its existing SQLite-backed memory store. The game policy's saved Q-table is ingested as inspectable learned parameters. This is not language-model weight training and does not imply transfer to other tasks.

## Import from a completed FUN benchmark

Download the workflow's \`bean-emperor-learning-benchmark\` artifact, which contains:
- \`bean-emperor-benchmark.json\`: summary metrics.
- \`bean-emperor-episode-ledger.jsonl\`: complete decision transition traces, including failed runs.
- \`bean-emperor-trained-policy.json\`: action-value table.

The \`GITHUB_SHA\` of the FUN workflow is the source commit identifier. Example:

\`\`\`sh
python -m bean.evaluation.emperor_gauntlet_ledger \
  --db ./data/bean_memory.db \
  --ingest ./bean-emperor-episode-ledger.jsonl \
  --policy ./bean-emperor-trained-policy.json \
  --source-commit <EXACT_FUN_GITHUB_SHA>
\`\`\`

The result is stored in BEAN's memory SQLite database, and the scoreboard includes per-source-combination training best, control mean, trained held-out mean, number of episodes and saved learned Q-policy receipts.

Receipts are content-addressed using SHA-256 and imported idempotently, without changing prior episode records. This checks internal consistency, not the authenticity of the person who produced the source data. Different builds are not combined silently.

## Architecture limits

BEAN Core can now consult retained scores and Q vectors; the game remains responsible for game action execution and Q-policy training. Integration into the BEAN general reasoning scheduler or automatic cross-domain policy transfer is *not* part of this change. The recorder's reward signal is specific to a fictional arcade game. No game reward is promoted as evidence of improved manufacturing reasoning or source verification.

See the experimental FUN draft PR: https://github.com/danieloculus0-bot/FUN/pull/2
