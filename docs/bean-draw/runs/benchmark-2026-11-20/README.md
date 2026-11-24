# Genuine BEAN drawing benchmark — 2026-11-20

This archive retains eight actual `qwen2.5:3b` drawing attempts from BEAN's Python Core: two teapot training attempts, then two sailboat attempts in each adaptive, frozen-memory and no-memory condition. Subjects were human-defined protocol challenges; geometry came from the model. There are six distinct PNG hashes because both adaptive and frozen attempts were byte-identical. No fixture artwork is included.

**No external pixel review reached the model during this benchmark.** Every file-review request timed out during the interrupted host session. The original receipts and [original summary](original/summary.json) retain `unavailable` feedback and null external scores. Textual model self-critique was available. The later [posthoc reviews and summary](posthoc/posthoc-summary.json) are separate observations, marked `posthoc: true` and `used_for_generation: false`; they did not influence either draft, the frozen snapshot, or model selection.

## Observed posthoc results

Scores use the [previously recorded rubric](benchmark-rubric.json), from 0 to 4. The reviewer inspected actual PNGs and knew the requested subject and arm path. These are subjective, unblinded host-model observations, with no human aesthetic evaluation or authenticated independent oracle.

| Held-out arm | Final coherence / recognition / composition | Last-minus-first scores |
| --- | --- | --- |
| Adaptive memory | 1 / 0 / 1 | 0 / 0 / 0 |
| Frozen memory | 1 / 0 / 1 | 0 / 0 / 0 |
| No memory | 1 / 0 / 1 | 0 / 0 / 0 |

Adaptive-minus-control scores were zero for every metric. No attempt reliably depicted the requested teapot or sailboat in this review. These observations establish no retained-memory advantage or drawing improvement. Only one held-out subject was tested; the first adaptive and frozen challenge starts from the same training evidence. Broad generalization and portfolio diversity remain unproven. No model weights were updated.

Inspect the actual final PNGs: [adaptive](original/heldout/adaptive/challenge_01/attempts/attempt_02.png), [frozen](original/heldout/frozen/challenge_01/attempts/attempt_02.png), [no memory](original/heldout/none/challenge_01/attempts/attempt_02.png), and [teapot training](original/training/adaptive/challenge_01/attempts/attempt_02.png). Each containing folder preserves both SVG/PNG drafts, immutable sidecars, raw inference records, the full model-call archive, run receipt, commands and process logs.

## Runtime, source and exact commands

- Source: `3fc06f4777a68b492928d6a08a0dd251977af895`, unchanged worktree for all four cells.
- Provider: Ollama `0.40.16`, CPU, existing BEAN `OllamaSketchProvider`.
- Model: `qwen2.5:3b`, 3.1B Q4_K_M; serving tag digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
- Protocol: [original/protocol.json](original/protocol.json), digest `fa0041e153552d9c9a709ab3ece1af8c48491c8c95a99f395280205331b42c78`. The seed is a protocol integer, not a calendar date. Each recorded cell used seed `20261131`, derived by adding its challenge number to `20261130`.
- [Source amendment](benchmark-source-amendment.json) was recorded before benchmark calls, adding model-authored composition planning and a 600-second CPU transport timeout without changing subjects, seeds, budgets or rubric.

Original command, run from the frozen checkout:

```sh
BEAN_REASONING_PROVIDER=ollama BEAN_OLLAMA_MODEL=qwen2.5:3b   /workspace/bean-venv/bin/python -m bean.creativity.drawing_benchmark   --protocol /workspace/bean-live-evidence/benchmark-protocol.json   --out /workspace/bean-live-evidence/benchmark   --review-dir /workspace/bean-live-evidence/benchmark-reviews   --review-wait 600
```

[original/execution.json](original/execution.json) preserves every exact child command, argument, seed and return code. All four processes returned zero; this establishes completed mechanics, not good art. Their retained stderr records a Python runpy module-import warning. Do not overwrite the original output directory when reproducing a run.

To reproduce the **original null-score summary** from this archive, using the matching BEAN source and local raster dependencies:

```sh
python -m bean.creativity.drawing_benchmark   --protocol docs/bean-draw/runs/benchmark-2026-11-20/original/protocol.json   --out docs/bean-draw/runs/benchmark-2026-11-20/original   --summarize-only
```

This reads the preserved original receipts; it does not inject later posthoc scores.

## Integrity, persistence and public review

[posthoc/artifact-verification.json](posthoc/artifact-verification.json) records verification of all run/sidecar/raw/SVG/PNG hashes. Every SVG was reproduced byte-for-byte from primitives in its archived actual model answer, and every PNG matched safe local rerasterization of its SVG. Artifact integrity is separate from subject recognition or authenticated model authorship.

The `journals/` folder contains deterministic `mtime=0` gzip archives of consistent SQLite online backups: training, adaptive, frozen and no-memory. Each backup's actual SHA journal chain was verified. [source-copy-manifest.json](source-copy-manifest.json) records source, raw-backup and compressed SHA-256 hashes, byte counts, journal tips and exact copied-file identities. Source database hashes were checked before and after backup and did not change. These are the new public drawing experiment's journals, not the owner's private checkpoints.

[public-review.json](public-review.json) binds every archived evidence file to its SHA-256 hash and records host-agent content review. The detached `public-review.sha256` binds that manifest; the manifest and its detached checksum exclude themselves from the file map to avoid self-reference. This review is not human aesthetic evaluation or proof of learned improvement.
