# BEAN vs Vaultbreaker — Free Range Beans research lab

**Status: experimental branch only. Not merged, not a production capability.**

BEAN faces a hidden four-symbol combination drawn from a **1,296-code** space (symbols 0–5, repeats allowed). The independent `Vault` returns only Mastermind-style exact-position and misplaced-symbol counts. BEAN eliminates all incompatible codes after each guess and attempts to crack the vault in at most nine turns.

## BEAN sees the scoreboard

Every attempted guess carries `scoreboard_seen` and `scoreboard_seen_sha256`, recorded **before** the independent oracle reveals its feedback. This includes previous games, wins, total reward, per-tactic reward/usage, current remaining candidates, and current episode reward. A genuine trainable dependency-free **5 → 8 → 3** neural controller takes scoreboard-derived input to select among three real strategies:

- `first`: first compatible code, no probe evaluation
- `minimax`: brute-force probes, minimize worst remaining feedback group
- `entropy`: brute-force probes, minimize summed squared group sizes

When training, the neural controller updates weights after the oracle computes each observed reward. No model output may forge a reward or success flag. Weight files are reloaded **from disk** before the frozen holdout. All arms face **the exact same unseen codes**: fixed first-candidate baseline, untrained neural, trained neural. BEAN Core's existing optimization selector also ranks measured implementations *when importable*, using empirical reward and replay evidence. This heuristic review is not independent proof of agent learning.

## Reward

Each turn receives `10 × log2(candidates_before/candidates_after) − 9 − 0.00002 × probe_checks + (100 if solved else 0)`. A missed nine-turn vault also loses 100 points. The logarithmic information term telescopes across a successful game, so adding more turns **cannot farm extra information points**. Faster correct solutions and fewer expensive probes are preferable.

## Historical evidence

The independent verifier replays **every guess**, verifies matching oracle feedback and exact remaining-set counts, recalculates reward, checks the pre-decision scoreboard digest, and rejects mismatches. Each episode is saved as immutable `*.jsonl.gz` with an individually hashed manifest. The existing `IndexedLedger` can rebuild an SQLite lookup cache from archives and retrieve each decision by its compact `T.<hash>` ID. The byte-exact full episode is an attachment inside the same compressed run. Failed games and reward penalties are retained.

**Important:** GitHub Actions artifacts are retention-limited. Durable recovery requires keeping or committing the original `archive/*.jsonl.gz` and matching `*.manifest.json`; the SQLite index is disposable, **not** the source of truth. This research lab does not automatically ingest previous GitHub Actions test records whose original XML has expired.

## Run

From BEAN repo root:

```bash
PYTHONPATH=. python research/persistent_ledger/indexed_recall/vaultbreaker.py --training 30 --holdout 15 --output vaultbreaker-evidence
PYTHONPATH=.:research/persistent_ledger/indexed_recall python -m unittest discover -s research/persistent_ledger/indexed_recall -p 'test_*.py' -v
```

On PowerShell, set `$env:PYTHONPATH = \". ;research/persistent_ledger/indexed_recall\".Replace(\" \",\"\")` first, then use `py` for the commands. Standard-library Python 3.11+; no additional packages or Ollama required for deterministic reproducibility.

Open `vaultbreaker-evidence/report.json` for all scoreboard totals. Each `training`, `fixed_baseline`, `untrained_neural` and `trained_neural` directory holds its own compressed archive and SQLite index. `neural_state.json` contains the actual trained weight arrays.

## Research limits

This experiment shows whether the policy updated weights and how it scored in a frozen matched holdout, **not** necessarily that neural training improved the strategy. If trained versus untrained shows no advantage, report that failure. The oracle is synthetic and fully deterministic, not a real-world verification or general autonomous competence test. BEAN Core selection is a rubric on measured strategies, not an LLM independently authoring strategies.
