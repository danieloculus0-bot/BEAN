# Automatic-vision drawing benchmark: retained failed memory contrast

This archive preserves genuine BEAN Python Core runs with Qwen choosing every geometric primitive and a separate Gemma evaluator receiving the actual rendered PNGs. The neutral **human-protocol subjects** were a teapot for training and a cat plus a sailboat for held-out evaluation. These challenges were not autonomous subject choices. No scripted rocket fixture or externally generated artwork was used.

**The intended adaptive-versus-frozen retained-learning comparison is invalid.** The 2400-character memory-context prefix truncation kept the older teapot evidence and removed newer cat feedback. Adaptive and frozen therefore received identical effective memory inputs for the sailboat challenge. Their identical images and zero reported score differences cannot demonstrate either a memory advantage or the absence of one. This is a retained measurement/wiring failure, not a successful learning comparison. [Context audit](memory-context-audit.json), [full-versus-truncated evidence](final-audit/integrity/context-truncation-detail.json), [actual prompt/context hashes](final-audit/integrity/memory-context-audit.json).

The recorded interval was 2026-11-23 21:49:52 CST to 2026-11-23 23:12:40 CST (Chicago). Original receipt timestamps remain UTC: 2026-11-24T03:49:52.461327+00:00 to 2026-11-24T05:12:40.591525+00:00; the directory date follows those original UTC records.

Seven fresh child processes completed, retaining **14 attempts, 13 actual SVG/PNG pairs, and one failed draft**. Every iteration, failure, raw artist answer, self-critique, image review, model selection and process log remains unchanged in [original/](original/). Process exit code zero did not turn the incomplete cell into complete matched evidence.

## Actual images and reported scores

The following are Gemma's model-reported coherence / requested-subject recognition / composition ratings on a 0–4 scale, not human evaluation or authenticated visual truth:

| Phase / subject | Adaptive final | Frozen-memory final | No-memory final |
| --- | --- | --- | --- |
| Training / teapot | 4 / 3 / 4 | Not a training arm | Not a training arm |
| Held-out / cat | 3 / 2 / 3 | 3 / 2 / 3 | 3 / 2 / 3 |
| Held-out / sailboat | 2 / 3 / 2 | 2 / 3 / 2 | Incomplete; excluded, not scored as zero |

The unchanged [original/summary.json](original/summary.json) records zero adaptive-minus-frozen differences across two held-outs, and zero adaptive-minus-no-memory differences on the one complete cat comparison. These are raw arithmetic results from the recorded ratings. The broken memory exposure prevents their use as retained-learning evidence. Averages over different complete-case sets must not be mistaken for an advantage.

The later [final host image audit](final-audit/final-host-audit-summary.json) inspected all nine unique actual PNGs and found no reliable teapot, cat or sailboat recognition. Its separate, unblinded host-model ratings disagree with Gemma's sometimes high confidence. No model weights were updated. Broad generalization and portfolio diversity remain unproven; added files or changed image hashes do not demonstrate learning. Later host observations were not supplied to generation and do not rewrite original model reports.

Inspect actual final PNGs: teapot [training](original/training/adaptive/challenge_01/attempts/attempt_02.png); cat [adaptive](original/heldout/adaptive/challenge_01/attempts/attempt_02.png), [frozen](original/heldout/frozen/challenge_01/attempts/attempt_02.png), [no memory](original/heldout/none/challenge_01/attempts/attempt_02.png); sailboat [adaptive](original/heldout/adaptive/challenge_02/attempts/attempt_02.png), [frozen](original/heldout/frozen/challenge_02/attempts/attempt_02.png). No-memory sailboat retains its [first valid PNG](original/heldout/none/challenge_02/attempts/attempt_01.png) and [failed second receipt](original/heldout/none/challenge_02/attempts/attempt_02.json).

## Preserved failures and corrections

No-memory sailboat attempt 2 failed with `ValueError: Required bounded text`: the actual model returned a 337-character description where the source required at most 300 characters. The unmodified [raw answer](original/heldout/none/challenge_02/attempts/attempt_02.raw.json) remains inspectable. No SVG, PNG or vision report was fabricated for it; no manual description truncation or geometry repair was used. The process returned zero because another draft existed, while benchmark validation correctly excluded the incomplete final cell.

One earlier posthoc host note was written before its image was actually inspected. It is explicitly invalidated and retained with a hash-linked correction under [prior-host-audit/images/](prior-host-audit/images/). The [final audit](final-audit/final-host-audit-summary.json) identifies both hashes, uses corrected observations and independently reinspects the actual image. Neither that premature note nor its correction influenced BEAN's generation. Original automatic Gemma feedback remains unchanged.

## Runtime, source and actual image review

- Artist: Ollama `0.40.16` CPU, `qwen2.5:3b` (3.1B, Q4_K_M), digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
- Evaluator: separate `gemma3:4b`, digest `68ceab7e468a31c988b44d5a4984a0e21f58c4f7158c6ce29c1804babac38df7`.
- Frozen source: `01090ba7c8c97855a7e3d352c3e9003e7278e972` for all cells.
- Protocol digest: `d8a7c99d4be1fe8813b1ab8d309c930cb5170ffa6a8787dfe3a35915e2d87e7e`; [protocol](auto-vision-benchmark-protocol.json), [preregistration](auto-vision-benchmark-preregistration.json), [source amendment before any benchmark calls](auto-vision-benchmark-source-amendment.json).

The image protocol is `blind_then_targeted_min_v1`: first send actual PNG bytes without the claimed subject, then send the same image with the target and blind observations. Each final metric is that dimension's minimum across the two reports. This rule reduces title priming; it does not guarantee recognition or evaluator correctness. Each successful attempt's `.vision.json` preserves both raw evaluator replies, parsed reports, image hash, model identity/digest and score rule. The image review is separate from Qwen's textual coordinate self-critique, and `independently_authenticated` remains false. Actual in-run image feedback was supplied to subsequent generation or final selection; preservation is not proof that the model used it effectively.

## Exact commands and reproduction

Run from the matching frozen source with both genuine local models installed:

```sh
BEAN_REASONING_PROVIDER=ollama BEAN_OLLAMA_MODEL=qwen2.5:3b \
  /workspace/bean-venv/bin/python -m bean.creativity.drawing_benchmark \
  --protocol /workspace/bean-live-evidence/auto-vision-benchmark-protocol.json \
  --out /workspace/bean-live-evidence/auto-vision-benchmark \
  --vision-model gemma3:4b
```

[original/execution.json](original/execution.json) preserves every exact child command, argument, seed, phase, arm and return code. Protocol seed `20261124` was offset by challenge number, producing `20261125` and `20261126`; these integers are identifiers, not dates. Each challenge reopened Core in a fresh interpreter. Adaptive and frozen began from the same training snapshot, while no-memory suppressed prior retrieval; the intended later adaptive exposure was then lost to truncation.

To reproduce the **historical machine summary**, use source `01090ba7c8c97855a7e3d352c3e9003e7278e972` and compatible image dependencies:

```sh
python -m bean.creativity.drawing_benchmark \
  --protocol docs/bean-draw/runs/auto-vision-benchmark-2026-11-24/original/protocol.json \
  --out docs/bean-draw/runs/auto-vision-benchmark-2026-11-24/original \
  --summarize-only
```

The archived summary was reproduced from the historical source after normalizing Python tuples to their serialized JSON arrays. Do not overwrite retained output directories. Later fixes or audits must remain separate from these original receipts.

## Integrity and public review

Original non-database files were copied byte-for-byte. Four `journals/*.sqlite3.gz` files are deterministic `mtime=0` gzip archives of consistent SQLite online backups, opened read-only at their source. Their actual SHA journal chains and every table row were checked against source databases; source file hashes remained unchanged. [source-copy-manifest.json](source-copy-manifest.json) records source, raw-backup and compressed SHA-256 hashes, byte counts, journal tips and copied-file identities. These are public experiment journals, not private owner checkpoints.

[Final integrity evidence](final-audit/integrity/artifact-integrity.json) retains the separate verifier's model-primitive-to-SVG replay, PNG rerenders, raw/sidecar/run/vision hash checks and failure retention. The archived audit's helper scripts and rerendered files are verification evidence, not another artist or synthetic originals.

[public-review.json](public-review.json) binds every archived file by SHA-256 and records host-agent content review of the generic experiment data. Detached `public-review.sha256` binds that manifest; the two exclude themselves to avoid self-reference. This review is not human aesthetic evaluation, provider authentication or proof of learning.
