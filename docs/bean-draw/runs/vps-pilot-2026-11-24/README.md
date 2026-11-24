# VPS drawing pilot: a model-chosen sunset subject

The existing BEAN Python SketchLab ran on the owner's **Contabo VPS** with the configured real Ollama artist **qwen2.5:7b** and a separate **gemma3:4b** image reviewer. The artist independently chose **“A Sunset Over a Quiet Beach”**, authored its instructions and every geometric primitive, made two attempts, received actual-image feedback before revising, and selected attempt 2. Both original SVGs and actual PNG previews are retained. No host-supplied geometry, canned fixture, external artwork or image-generation service supplied these drawings.

**Real model generation and artifact integrity are verified. A recognizable sunset, successful revision and retained learning are not.** Both original attempts retain `host_reported_not_satisfactory`. The original artist's final selection remains intact even where it conflicts with external observations.

Inspect the actual images: [attempt 1 PNG](original/artifacts/attempt_01.png), [SVG](original/artifacts/attempt_01.svg), [receipt](original/artifacts/attempt_01.json); [attempt 2 PNG](original/artifacts/attempt_02.png), [SVG](original/artifacts/attempt_02.svg), [receipt](original/artifacts/attempt_02.json). [Full run receipt](original/artifacts/run.json), [all artist calls](original/artifacts/model_calls.json).

## Runtime, source and scope

The run began at **2026-11-24 09:05:21 CST** and ended at **09:10:38 CST** (Chicago). Original receipts use UTC: `2026-11-24T15:05:21.736108+00:00` through `2026-11-24T15:10:38.097218+00:00`.

- Artist: Ollama **0.40.18**, **qwen2.5:7b**, 7.6B Q4_K_M; digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`.
- Evaluator: **gemma3:4b**, 3.9B Q4_K_M with actual image projector; digest `68ceab7e468a31c988b44d5a4984a0e21f58c4f7158c6ce29c1804babac38df7`.
- Executed source: **`54b0a4d2c17face7ffbf3d016ef348c5a055164a`**. Each of the four recorded runtime module hashes matches its pinned Git blob; the local replay used the identical drawing and rasterization modules.
- Task: `contabo-pilot-20261124`; run ID `797a888c-4a33-4384-abcf-02ff43b11e4b`; seed `202611241`.

This pilot used the existing **SketchLab CLI**. It is **not live execution proof for the later Core orchestration/adapter changes in PR #513**. Reusing an existing configured provider establishes genuine provider access, not integration of every new runtime route. The 7B artist was not compared against the earlier 3B artist on matched tasks, seeds and controls; a larger model or a changed image cannot demonstrate learning.

[provider-integrity.json](original/provider-integrity.json) preserves the source-side provider identities, capabilities and **13 model-blob SHA-256 records**. The local export audit checked that receipt's hash and internal consistency. The model blobs themselves were not downloaded for a second local rehash; the receipt is not independently authenticated provider identity. [Provider version](original/provider-version.json).

## Actual feedback and its limits

Every `.vision.json` preserves two real image-review passes: actual PNG pixels first without the subject title, then the same PNG with the target and blind observations. The protocol `blind_then_targeted_min_v1` retains both raw responses and takes the dimension-wise minimum of their reported ratings. Each report is bound to the actual PNG hash.

Gemma's title-blind reports called attempt 1 a **balance scale** and attempt 2 a **circuit diagram**. Its target-aware prose explicitly said both were unrelated to the claimed sunset. Nevertheless, its normalized requested-subject recognition scores were 3/4 and 2/4. This contradiction is retained as evaluator error, not treated as evidence that either picture depicts a sunset. Its coherence / recognition / composition ratings were **2 / 3 / 3** then **1 / 2 / 2**. [First image report](original/artifacts/attempt_01.vision.json), [second image report](original/artifacts/attempt_02.vision.json).

The [local audit](audit/initial-export-audit.json) verified that the first attempt's complete image-feedback text and PNG hash actually appear in **both the planning prompt and geometric drawing prompt for attempt 2**. This is evidence of feedback delivery, not effective use. Qwen's textual self-critique is recorded separately. The artist cannot inspect pixels directly and was asked to weigh external image feedback separately from its confidence.

The later [host visual review](audit/host-visual-review.json) was written after both actual PNGs were displayed. With the title supplied, its observer weakly associated attempt 1's upper circle and line with a sun and horizon, rating recognition **1/4**. It could not recognize a sunset in attempt 2, rating recognition **0/4**. Its coherence / recognition / composition ratings were **1 / 1 / 2** then **1 / 0 / 1**. These unblinded host-model observations do not confirm a successful revision. They were not fed to the artist and do not replace the original Gemma reports or artist selection.

No model weights were updated. The delivered prior-session memory was an empty JSON array, and this single-subject pilot has no adaptive/frozen/no-memory controls or held-out generalization test. Attempt receipts retain `weights_updated=false` and `independent_visual_verification=false`. The separate audit reports explicitly mark learning improvement unverified. Human aesthetic evaluation is unavailable.

## Exact executed entry point

The [launch receipt](launch-receipt.json) records the actual command, working directory and neutral provider environment. The subject argument was omitted so the model chose the subject. From `/opt/bean/drawing-src`, the command was:

```sh
BEAN_REASONING_PROVIDER=ollama \
BEAN_OLLAMA_MODEL=qwen2.5:7b \
BEAN_OLLAMA_URL=http://127.0.0.1:11434 \
  /opt/bean/draw-venv/bin/python -m bean.creativity.sketch_lab \
  --db /var/lib/bean/drawing/art_history.sqlite3 \
  --out /var/lib/bean/drawing/runs/20261124-vps-pilot \
  --task-ref contabo-pilot-20261124 --require-live \
  --attempts 2 --all-attempts --backend stdlib \
  --seed 202611241 --vision-model gemma3:4b
```

The worker reused the existing local Ollama service. The launch receipt records that this pilot did not use the primary private database or restart the primary Core. Reproduction requires the identified source, genuine configured providers, compatible image dependencies and a fresh output directory; retained run directories must not be overwritten.

## Preserved export and independent artifact replay

All **19 file hashes** in the original [export-hashes.json](original/export-hashes.json) were checked against the downloaded files before curation. Both raw drawing responses decode to the **exact SVG bytes**. Local safe CairoSVG rerenders match the actual exported PNGs **pixel-for-pixel in RGB**, with no platform mismatch. Sidecar, raw-response, model-call and linked vision-receipt hashes also match. These checks verify bytes and pipeline execution, not artistic quality.

Every file in the bounded public drawing export is copied unchanged under [original/](original/). This includes the [stdout drawing receipt](original/pilot.stdout.json), [stderr warning](original/pilot.stderr.log) and [worker status](original/pilot-systemd-status.txt). Stderr emitted a `runpy` warning that SketchLab was already imported before module execution; the worker nevertheless returned exit status 0 and retained both valid artifacts. No private SSH, host configuration or Actions logs are included. The absolute `/var/lib/bean/drawing/...` paths in retained receipts are original provenance, not links on this website. Use the relative artifact links above.

The first export explicitly [omitted its journal](original/journal-not-exported.json). At the time of the initial local audit, journal SHA-chain and sidecar-to-journal payload matching were **unavailable**. This initial omission record and audit are preserved without alteration; any later bounded journal verification is recorded separately.

The [subsequent bounded journal export](journal-followup/verification.json) corrected an overly strict exporter check: the existing Core records **two draft trials plus one run-completion trial**. All three belong to this exact task and run. A consistent read-only backup was verified remotely, then the [local follow-up audit](audit/journal-followup-audit.json) independently checked its compressed/uncompressed hashes, complete SHA chain, both exact sidecar payloads, final run payload and retained-context hash. The [actual journal backup](journal-followup/drawing-journal.sqlite3.gz) contains only these three public drawing events. The original source database was reported unchanged by the remote verifier. No primary private Core database or unrelated history was exported. [Exact bounded collection script](audit/collect-journal-followup.sh).

This follow-up reopened serialized records in a separate process and verified two retained drawing-context records. It made **no model call** and does not establish that a subsequent generation used them or improved. The original omission was not erased, and no draft was regenerated to repair the collector. [Source/copy hashes](source-copy-manifest.json).

The archive's local verifier is [audit_pilot_export.py](audit/audit_pilot_export.py). It never contacts a model or server and never alters exported originals. Its scope is artifact replay, hashes, recorded source identity and feedback delivery. Publication review and later visual/journal observations are separate records.

[Artifact publication review](artifact-public-review.json) binds the exact model-run files used by the gallery. The full archive's [public review](public-review.json) binds all archived files by SHA-256; its [detached digest](public-review.sha256) excludes self-reference. This is host-agent content review, not human aesthetic approval or proof of learning.
