# BEAN Lab009 frozen replay research ledger

This is an **append-only research snapshot** of BEAN Bridge's synthetic Lab009 experiment, not a change to BEAN's runtime decision policy. It is stored alongside the existing compressed persistent ledger without modifying the original events or scoreboards.

- `event_log.csv.gz`: **14** events, including original baseline, frozen post-restart score, online score, acceptance count, Core event total, the four OS/Python matrix jobs, and the four other triggered passing workflows.
- `scoreboard.json`: small rebuildable research score summary, exact source SHA, CI run, classification, and SHA-256 of both decompressed CSV and gzip archive.
- Source: [BEAN Bridge draft PR #46](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/46), revision `86d6733861c9114c749077584ec96a7f4da74f24`.
- CI proof: [GitHub Actions run 39534731732](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/39534731732), Windows/Ubuntu with Python 3.11/3.12, **4/4 jobs passed**. Four other PR workflows passed, each named in the compressed event log.

## Scores (synthetic, 3 fixture questions)

| Phase | Correct | Meaning |
|---|---:|---|
| Original baseline | 0/3 | Before evidence was acquired |
| Frozen post-restart | 2/3 | Checked **before** any new T2 evidence |
| Online post-investigation | 3/3 | Includes a novel answer acquired **during** T2 |
| Model outputs accepted | 0/3 | Gate acceptance, **not** a standalone model-accuracy estimate |

BEAN Core journal recorded **21 research events** in the run. Neither 21 events nor 4/4 passing jobs means BEAN's model learned a new general skill. This is evidence of persistent verified-definition retrieval and bounded online evidence acquisition in a synthetic environment.

## Integrity and replay

`gzip -dc event_log.csv.gz` restores the CSV. SHA-256 of restored CSV must equal `scoreboard.json:event_log_csv_sha256`; SHA-256 of compressed bytes must equal `event_log_gzip_sha256`. Every event carries its evidence URL and classification. The original 34-row baseline, 21-row replay ledger, and full-Core matrix remain untouched.

This ledger is **not automatically read by BEAN Core**. It serves as an experimental, versioned score archive until an explicit read/replay adapter is separately implemented and tested. No real-world or proprietary data were recorded.
