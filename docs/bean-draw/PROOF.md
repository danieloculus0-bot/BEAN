# BEAN Draw execution evidence

These are actual BEAN Python Core model runs, triggered by host CLI. The model chose subjects and every geometric primitive. No host-authored geometry, scripted rocket answers, image generation service, or external artwork was used for these live entries. The two rocket fixtures remain separate synthetic tests.

The artwork is currently weak. Artifact integrity is verified; recognizable subjects and improved drawing skill are not established. External ratings are unblinded Codex visual observations, not human evaluation or independently authenticated ground truth.

## Recorded original sessions

| Model-chosen subject | Attempts | Actual artifacts | Observed outcome |
| --- | --- | --- | --- |
| Mysterious underwater forest | 2 | No SVG or PNG | Both failed validation; model repeated out-of-range coordinate `260` |
| Magnificent snow-covered mountain range | 2 | 2SVG +2PNG | External coherence/recognition/composition1/1/1 then1/0/1; recognition worsened; model selected first draft |
| Vibrant sunflower field | 2 | 2SVG +2PNG | Pixel reviewer unavailable during run; posthoc ratings1/0/1 for both; no observed improvement |
| Whimsical flying dragon | In progress | Pending | No success claimed yet |

[Underwater failure receipts and original model calls](runs/2026-11-19/subject-1/run.json), [mountain run](runs/2026-11-19/subject-2/run.json), [sunflower run](runs/2026-11-19/subject-3/run.json), [posthoc sunflower review](runs/2026-11-19/posthoc-subject3.json), [actual artifact/journal verification](runs/2026-11-19/verification.json).

Every run folder retains model_calls.json, attempt_XX.raw.json, immutable attempt receipts, all successful SVGs/PNGs, and run.json. No failures were replaced. Sidecars bind to the actual fresh drawing experiment's SHA-chained SQLite Core journal. The owner's private checkpoints were not loaded or published.

## Runtime and source

Ollama `0.40.16` CPU; qwen2.5:3b, Q4_K_M, 3.1B. Serving model digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`. All six downloaded model blob hashes were recomputed and matched their content addresses.

Original source commits: f0aa5ba64614d1ef5c0fcbc9a851e505ec96d1d8 (failed forest), 2db4f232ef6f2385375a79bd87c3df77501999ec (mountains), 3fc06f4777a68b492928d6a08a0dd251977af895 (model composition planning, sunflowers and subsequent trials). Each run records exact module hashes where available. The source was evolving during the first two sessions; later sessions use an unchanged worktree. Do not treat a Git SHA alone as a clean-tree attestation.

## Reproduce a live session

```sh
python -m pip install 'CairoSVG==2.8.2' 'drawsvg>=2,<3'
export BEAN_REASONING_PROVIDER=ollama
export BEAN_OLLAMA_MODEL=qwen2.5:3b
export BEAN_OLLAMA_URL=http://127.0.0.1:11434
python -m bean.creativity.sketch_lab --db drawing-core.sqlite3   --out new-subject --task-ref original-subject --require-live   --attempts 2 --all-attempts --backend stdlib --seed 20261122   --review-dir reviews --review-wait 600
```

Use actual spaces in flags: `--attempts 2 --seed 20261122 --review-wait 600`. Existing directories cannot be overwritten. A missing provider fails explicitly. A real pixel reviewer must inspect each requested PNG before supplying its hash-bound report; otherwise evaluation remains unavailable. Full commands, optional subjects and file-review protocol are in [BEAN_SKETCH_LAB.md](../BEAN_SKETCH_LAB.md).

## Measurement and checks

A held-out protocol was preregistered for teapot training and sailboat evaluation with adaptive, frozen-memory and no-memory controls. Execution is pending. No retained-learning improvement or model weight update is claimed. A single held-out subject cannot establish broad generalization or portfolio diversity.

Latest targeted tests:121passed plus12subtests. Broader CI Core jobs passed Linux/Windows on source3fc06f4; its one live llama.cpp smoke failed during upstream web-UI provisioning before inference. A minimal build fix is under test. Local full-Core run had1462passes,15skips,7failures and5errors from restricted loopback, missing browser, and incompatible preinstalled optional MCP SDK; environment rechecks are ongoing. Exact final-head CI remains required before merge.
