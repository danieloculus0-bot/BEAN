# Persistent Ledger: compact event history and BEAN scoring (experimental)

Status: research specification only. No runtime wiring, self-modification, or production rollout.

## Purpose
Keep a minimal **active scoring memory** (target: kilobytes per experiment/policy) while preserving exact historical measurements in a versioned, compressed GitHub event log. The complete log is the source of truth; scores are cheap, rebuildable summaries, not a claim of BEAN intelligence or truth.

## Format v1
- Readable source: `research/anticipatory_ledger_20261020.csv`
- Compressed snapshot: `research/anticipatory_ledger_20261020.csv.gz` (standard gzip, decompress to UTF-8 CSV)
- CSV columns: `date,experiment,metric,condition,value,unit,sample,source`
- Current snapshot: 34 synthetic benchmark observations, 3,566 bytes uncompressed, 805 bytes gzipped.
- SHA-256 of uncompressed CSV: `0401de4da617040f26da5f7473fd90ae538636b1c33706cdcb00b926f8f91a11`.
- Snapshot recovery test: gzip decompression exactly reproduces CSV bytes.

## Rules for subsequent records
1. Append observations, including **failures and regressions**. Never silently rewrite old outcomes. Batch commits rather than committing every event.
2. Record `run_id`, test code revision, environment, source provenance, and `synthetic | measured` evidence status in an accompanying run manifest when new runs are added. V1 rows alone do not contain all this metadata.
3. Preserve numeric units, sample count, comparator, and test conditions. Compare only matched conditions (including sample strategy, hardware and model revision).
4. Keep independent evidence verification distinct from source labels and asserted verification. A passing heuristic screen is not independent authentication.
5. Keep GitHub logs public-data-only; never commit typed private user messages, secrets, or unredacted personal data.
6. Periodic compressed snapshots are for long-term storage, not live transaction writes or a replacement for local durable storage.

## Proposed compact scoring state (not implemented)
For each `experiment + metric + condition + candidate`, maintain a small bounded record:
- `n`, successes/failures if applicable, rolling mean/variance, latest timestamp, baseline ID, and last provenance digest.
- Track separate axes: **correctness, evidence quality, computational cost, adaptation, persistence**.
- Report raw values and deltas against matched baselines first. A single overall BEAN score is **not calibrated or adopted**; any future composite requires declared weights, reproducible held-out tests, and uncertainty intervals.
- Keep recent-window and lifetime statistics separately to detect drift without discarding history.
- Rebuild the active score state by replaying archive events. Version score algorithms, so historical evidence can be re-scored without changing original records.

## Research acceptance tests
- Reproducible gzip round-trip and checksum.
- Replay produces identical score state after restart.
- Duplicated/correlated evidence does not inflate independence.
- A counterexample or environment change revises candidate rankings.
- Scoring does not claim improvement unless a matched held-out baseline is beaten.
- Measure actual Jetson RAM, CPU/GPU and latency before claiming hardware savings.

This is a **proposal**, not an integrated BEAN subsystem.
