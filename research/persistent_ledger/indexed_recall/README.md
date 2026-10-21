# BEAN testing BEAN: compressed indexed recall (experimental)

Goal: **every JUnit test and original report is exactly retrievable**, including failed, skipped and repeated cases. An immutable compressed archive is the source of truth; a local SQLite cache is only an acceleration index that can be rebuilt and checked.

## What this prototype really does

- JUnit importer keeps the original XML bytes as an archived attachment, plus individually addressable test cases.
- Hierarchical identity is supplied by run ID, test name, and a `T.<24-hex>` SHA-256-derived event reference. Event and archive SHA-256 values are verified during rebuild; duplicates remain distinct.
- The output archive is gzip JSONL with a manifest containing one row per test. The index stores searchable case identifiers, outcomes and complete case records. Losing the index does **not** lose the archived source data.
- A computed scoreboard tracks passes, failures, skips and errors without trusting a generated summary.
- BEAN Core's existing `bean.optimization.selection.rank_improvements` chooses between **two predesigned retrieval strategies** using independently measured exactness and lookup speed. The engine does **not** propose its own implementations or establish model learning.
- A four-job Windows/Linux and Python 3.11/3.12 CI matrix measures evidence completeness and timings.

## Try it

Linux, from the repo root:

```bash
PYTHONPATH=research/persistent_ledger/indexed_recall:. python -m unittest discover -s research/persistent_ledger/indexed_recall -p 'test_*.py' -v
PYTHONPATH=research/persistent_ledger/indexed_recall:. python research/persistent_ledger/indexed_recall/benchmark.py --out recall.json
```

PowerShell, from the repo root:

```powershell
$env:PYTHONPATH = 'research/persistent_ledger/indexed_recall;.'
py -m unittest discover -s research/persistent_ledger/indexed_recall -p 'test_*.py' -v
py research/persistent_ledger/indexed_recall/benchmark.py --out recall.json
```

## Boundaries and next work

This is **not automatically collecting all historical tests**. Some original JUnit files were only retained as GitHub Actions artifacts, which can expire. Missing originals cannot be reconstructed from aggregate scores. We must wire CI to retain each original JUnit and associated logs before promising complete portfolio history.

The prototype does not implement neural retrieval or change BEAN's reasoning. A neural model should learn which experiment, run, or candidate evidence is relevant; **exact record retrieval must remain deterministic and hash-checked**, otherwise a plausible neural guess could masquerade as a test receipt. A future independent evaluation should compare a frozen learned ranker to keyword/hash indexes on held-out cases, across restarts and model revisions. Avoid shipping secrets and personal information to a public archive.

The index duplicates some evidence on disk: benchmark **both latency and storage overhead** and compare alternative sharded archives. Keep the prior experimental ledger, its compressed baselines, and all previous scoreboards intact.
