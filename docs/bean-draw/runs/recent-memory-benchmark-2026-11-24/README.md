# Corrected recent-memory drawing experiment

BEAN's existing Python Core completed seven fresh-process cells with a genuine local Qwen artist and separate Gemma image reviewer. All **14 attempts produced original SVGs and actual PNG previews**, retaining all raw artist replies, textual critiques, two-pass image reviews, selections, journal events and process logs in [original/](original/). The subjects were **human-protocol challenges**: a teapot for training, then an umbrella and a bicycle for held-out evaluation. These are not autonomous subject choices or synthetic rocket fixtures. Every primitive came from the actual artist model; no host geometry, manual artwork repair or image-generation service supplied the drawings.

**Recent feedback delivery is now verified; improved recognizable drawing and retained learning are not.** The [actual-file audit](audit/integrity.json) replayed model primitives into byte-identical SVGs, rerendered PNG pixels, checked linked receipts and verified Core journal chains. The [separate host image audit](audit/final-visual-review.json), written after inspecting every actual PNG, found no recognizable final teapot, umbrella or bicycle. It did not confirm the automatic evaluator's apparent gains. Human aesthetic evaluation remains unavailable.

The run began at 2026-11-24 06:53:10 CST and completed at 08:16:44 CST (Chicago). Original UTC timestamps remain in the receipts: 2026-11-24T12:53:10.794262+00:00 through 2026-11-24T14:16:44.146230+00:00.

## What the matched controls actually received

The [preregistered protocol](recent-memory-benchmark-preregistration.json) uses the same artist, evaluator, source, per-challenge seed and two-attempt budget in adaptive, frozen-memory and no-memory arms. All arms start from the same public-safe training experiment. Each cell opens Core in a separate Python interpreter; no private owner checkpoint was loaded or published.

| Held-out challenge | Adaptive delivered memory | Frozen delivered memory | No-memory delivered memory |
| --- | --- | --- | --- |
| Umbrella | Both teapot feedback records | Same teapot records | Empty array |
| Bicycle | Both newer umbrella feedback records | Original teapot records | Empty array |

Whole JSON context records and their SHA-256 hashes appear in the actual drawing prompts. The first adaptive/frozen challenge is an expected matched baseline and is excluded from the retained-memory effect estimate. The later bicycle challenge is the **one eligible adaptive/frozen contrast**. Both held-outs have eligible adaptive/no-memory contrasts. [Original summary](original/summary.json), [actual delivery and hash audit](audit/integrity.json).

The previous [oldest-first truncated-memory experiment](../auto-vision-benchmark-2026-11-24/README.md) remains preserved as an invalid memory-exposure comparison. This corrected run does not repair, replace or reinterpret those original receipts.

## Actual images and evaluator disagreement

Gemma's final coherence / requested-subject recognition / composition ratings below use a 0–4 scale. They are **model reports**, not authenticated ground truth:

| Phase / subject | Adaptive final | Frozen-memory final | No-memory final |
| --- | --- | --- | --- |
| Training / teapot | 3 / 1 / 3 | Not a training arm | Not a training arm |
| Held-out / umbrella | 4 / 4 / 3 | 4 / 4 / 3 | 3 / 4 / 3 |
| Held-out / bicycle | 3 / 3 / 4 | 3 / 2 / 3 | 3 / 3 / 2 |

For the single eligible bicycle adaptive/frozen contrast, Gemma's reported difference is coherence **0**, recognition **+1**, composition **+1**. Against no-memory, the two-challenge means are **+0.5**, **0**, **+1**. These are small-sample rating arithmetic, not demonstrated learning. Adaptive mean last-minus-first ratings across the two held-outs are coherence **+0.5**, recognition **0**, composition **+1**; the corresponding frozen values are **0 / −1 / +0.5**, and no-memory **−1 / −0.5 / −0.5**. They describe iteration under this evaluator, without establishing better recognizable artwork.

The later host observer inspected all 14 PNGs, including all 12 distinct byte hashes. It rated final subject recognition **0 in every cell** and coherence **1** throughout. Adaptive bicycle attempt 1 weakly suggested wheels with the title supplied (recognition 1), while attempt 2 lost that cue (recognition 0). The observer therefore found no final recognition advantage for adaptive memory over either control. Its joint portfolio diversity rating was 2/4, with repeated circles, rectangles and long lines across subjects. These are separate, unblinded host-model reports, not human judgment, and were **not supplied to generation**. Every earlier host observation is also retained in [audit/earlier-host-observations/](audit/earlier-host-observations/).

Inspect the actual final PNGs: teapot [training](original/training/adaptive/challenge_01/attempts/attempt_02.png); umbrella [adaptive](original/heldout/adaptive/challenge_01/attempts/attempt_02.png), [frozen](original/heldout/frozen/challenge_01/attempts/attempt_02.png), [no memory](original/heldout/none/challenge_01/attempts/attempt_02.png); bicycle [adaptive](original/heldout/adaptive/challenge_02/attempts/attempt_02.png), [frozen](original/heldout/frozen/challenge_02/attempts/attempt_02.png), [no memory](original/heldout/none/challenge_02/attempts/attempt_02.png). Every first draft and SVG is alongside its final draft.

## Source, providers and feedback

- Frozen source: `bb7128d76a6c210d84234326576ef6bc7f1e2509`. [Recorded module verification](audit/runtime-source-verification.json) matches each recorded runtime module hash against its pinned Git blob and unchanged execution worktree.
- Artist: Ollama **0.40.16**, CPU, **qwen2.5:3b**, 3.1B Q4_K_M; digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
- Evaluator: **gemma3:4b**, 3.9B Q4_K_M with its actual image projector; digest `68ceab7e468a31c988b44d5a4984a0e21f58c4f7158c6ce29c1804babac38df7`.
- Protocol digest: `85fef0d10c79300b4ee4cec3d0ff93a9ffce324d53282b7272826a6508a41ff7`; [protocol](recent-memory-benchmark-protocol.json), [preregistration before provider calls](recent-memory-benchmark-preregistration.json).

The evaluator protocol `blind_then_targeted_min_v1` sends actual PNG bytes first without the claimed subject, then with the target and blind observations. Each final dimension is the minimum of its two reported values. Both raw responses and image hashes survive in every `.vision.json`. This reduces title priming without guaranteeing recognition. In-run visual feedback is separate from Qwen's textual self-critique and was delivered for revision. Preserving feedback and changing geometry do not prove that the model used it effectively. All results retain `weights_updated=false`, `learning_improvement_verified=false` and `independently_authenticated=false`.

## Exact execution and reproducibility

Run from the pinned source with both genuine local providers installed. Use a fresh output directory:

```sh
BEAN_REASONING_PROVIDER=ollama BEAN_OLLAMA_MODEL=qwen2.5:3b \
  /workspace/bean-venv/bin/python -m bean.creativity.drawing_benchmark \
  --protocol /workspace/bean-live-evidence/recent-memory-benchmark-protocol.json \
  --out /workspace/bean-live-evidence/recent-memory-benchmark \
  --vision-model gemma3:4b
```

[original/execution.json](original/execution.json) preserves all seven exact child commands, subjects, seeds, memory modes, budgets and return codes. Protocol seed `202611240` was offset by challenge number, yielding `202611241` and `202611242`; these identifiers are not calendar dates. All processes returned zero, and every planned attempt has a valid SVG/PNG pair. There was no failed draft to replace in this run; historical failures remain in their separate archives.

The original summary was independently recomputed from the frozen source and matched after JSON normalization. For later recomputation, copy [original/](original/) into a scratch directory and use `python -m bean.creativity.drawing_benchmark --protocol <scratch>/protocol.json --out <scratch> --summarize-only` from the pinned source. Do not overwrite archival originals. Provider determinism, broad generalization and human recognition remain unproven.

## Immutable evidence and public review

Original non-database files were copied byte-for-byte. Four `journals/*.sqlite3.gz` files contain consistent SQLite online backups opened read-only at their source. Deterministic `mtime=0` gzip contents were decompressed and compared, every table row matched the source, and all SHA journal chains verified. Source database bytes remained unchanged. [source-copy-manifest.json](source-copy-manifest.json) records copied-file hashes, backup and compressed hashes, byte counts, journal tips and actual runtime source identities. [audit_recent_memory_run.py](audit_recent_memory_run.py) and [archive_recent_memory.py](archive_recent_memory.py) are verification/archive helpers, not drawing generators.

[public-review.json](public-review.json) binds every archived file by SHA-256 after host-agent content review of these generic public drawing experiments. [public-review.sha256](public-review.sha256) binds that manifest; both exclude themselves from its file map to avoid self-reference. This review is not human aesthetic evaluation, provider authentication or proof of learning.
