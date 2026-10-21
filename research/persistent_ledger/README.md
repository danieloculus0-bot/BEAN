# BEAN Persistent Compressed Scoring Ledger (research only)

**Two separate records. Do not replace either.**

1. **Historical baseline:** `../anticipatory_ledger_20261020.csv.gz` (34 original aggregate KPI rows; never rewritten).
2. **Replay event ledger:** `replay_event_log.csv.gz` (gzip CSV; append records for every pass, including failures). Columns: `pass_id,test,status,value,baseline,unit,evidence,ref,source_sha256`.
3. **Active scoreboard:** `scoreboard.json` (compact snapshot, updated after every pass; rebuildable from the event log and referenced original KPI baseline).

Each pass appends six assertion outcomes plus a `score_refresh` row. `score_refresh` reflects the referenced synthetic benchmark KPI, **not** a new independent accuracy measurement. Duplicated deterministic tests verify reproducibility, **not learning progress**. `latest_event_hash` chains the event rows with SHA-256 for simple tamper detection; Git commits version history. Host attestation and hashes do not independently authenticate evidence.

Recovery: decompress both gzip CSV files, verify the baseline SHA-256 from `scoreboard.json`, reconstruct test counts and latest score refresh, and compare the score snapshot. Failed tests and any future regression must remain visible.

Experiment executed on an isolated x86_64 CPU container; not Jetson or the live BEAN core. No BEAN runtime wiring or model updates are authorized by these logs.

## Lab009 frozen-versus-online scoring (2026-10-21 UTC)

See [lab009_20261020/](lab009_20261020/README.md) for its distinct 14-event gzip log, reproducible SHA-256 receipt, and compact scoreboard.

- Baseline **0/3**, frozen after restart **2/3**, after new online research **3/3**; **0/3** model outputs accepted.
- [Windows/Linux matrix](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/39534731732): 4/4 passed using pinned BEAN Core, plus four other passing PR workflows at the same Bridge source commit.
- The third correct answer was acquired during evaluation, not retained beforehand. Synthetic evidence retrieval is **not** demonstrated weight learning or autonomous strategy improvement.
- This adds a new experiment-specific compressed log and scoreboard. Older baselines and snapshots are untouched; no BEAN runtime integration is implied.
