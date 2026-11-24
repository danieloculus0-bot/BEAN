# BEAN Draw: actual execution evidence

BEAN's Python Core generated these drawing instructions and geometric primitives through real local model calls. SVGs were rendered from those exact primitives, then rasterized into PNGs. No image-generation service, externally supplied artwork, or manually supplied drawing geometry was used for the live entries. Rocket fixtures remain a separate synthetic-test view.

**Real generation is verified. Recognizable depictions and retained-learning improvement remain unproven.** Model confidence is a report, not independent visual verification.

## Original model-chosen subjects

| Model-chosen subject | Preserved attempts | Actual output | Observed result |
| --- | --- | --- | --- |
| Mysterious underwater forest | 2 | No SVG/PNG | Both responses contained an out-of-range coordinate; failures retained |
| Snow-covered mountain range | 2 | 2 SVG + 2 PNG | External host-model coherence/recognition/composition ratings 1/1/1 then 1/0/1; recognition worsened |
| Sunflower field | 2 | 2 SVG + 2 PNG | Image review unavailable during execution; later host-model inspection 1/0/1 for both |
| Whimsical flying dragon | 2 | 2 SVG + 2 PNG | Actual pixel feedback reached the revision; host-model ratings stayed 1/0/1 |
| Repeated dragon, automatic-review pilot | 2 | 2 SVG + 2 PNG | Gemma overreported recognition; host inspection did not confirm improvement |

These are three distinct successful **model-chosen subject labels**, not three verified recognizable depictions. The pilot repeated a subject; it is not additional subject diversity. The artist's final selection is preserved even when visual inspection disagrees with its claims.

Original receipts: [forest failures](runs/2026-11-19/subject-1/run.json), [mountains](runs/2026-11-19/subject-2/run.json), [sunflowers](runs/2026-11-19/subject-3/run.json), [dragon](runs/2026-11-20/subject-4/run.json). [Posthoc sunflower review](runs/2026-11-19/posthoc-subject3.json) did not influence those drafts.

[Actual artifact/Core-journal verification](runs/runtime/verification.json) and [joint original-portfolio review](runs/runtime/portfolio-review.originals.json) distinguish byte integrity from low observed visual diversity. Every draft, failure and critique is retained. These are fresh public-safe drawing experiment journals; the owner's private checkpoints were not loaded or published.

## Controls, feedback and measured limits

1. [First matched benchmark](runs/benchmark-2026-11-20/README.md): eight genuine attempts, teapot training and sailboat held-out evaluation. Every file survived; all live visual-review requests timed out during a paused session. Original scores remain null. Separate posthoc host-model reviews were 1/0/1 in all conditions. They did not influence generation.
2. [Automatic-review pilot](runs/pilot-vision-2026-11-24/posthoc-audit.json): a real Gemma vision model received actual dragon PNGs. With the title visible it confidently described a dragon that this host reviewer could not recognize. Both false-positive reports remain intact. Subsequent review uses a title-blind actual-image pass followed by a target-aware actual-image pass, with dimension-wise minimum ratings and both raw reports retained. This reduces one source of priming; it does not make the evaluator a truth oracle.
3. [Two-pass matched benchmark and audit](runs/auto-vision-benchmark-2026-11-24/README.md): 14 genuine attempts, 13 SVG/PNG pairs and one retained validation failure. Its adaptive/frozen **learning-exposure comparison is invalid**: the old 2400-character oldest-first context prefix excluded fresh feedback. Actual prompts and responses were identical. Descriptive Gemma scores must not be interpreted as evidence for or against a retained-memory benefit. Independent host-model inspection still found poor subject recognition.
4. A corrected run is in progress with whole JSON summaries selected newest first. It uses teapot training and new umbrella/bicycle held-out challenges, all three memory conditions, two attempts per cell, the same artist/evaluator/seeds/budgets, and fresh Core processes. New receipts store the actual delivered context records/hash. Comparison guards reject missing, stale, undelivered or incorrectly frozen memory. The first adaptive/frozen held-out case is an expected matched baseline, not evidence of adaptation. Results will be added after execution and audit.

All experiments keep `weights_updated=false` and `learning_improvement_verified=false`. Changed geometry, more files, self-satisfaction and higher model scores do not establish learning. Human aesthetic evaluation is unavailable. External Codex/Gemma observations are model reports, not authenticated ground truth.

## Runtime and source provenance

- Artist: Ollama **0.40.16**, **qwen2.5:3b**, 3.1B Q4_K_M, CPU. Model digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
- Automatic evaluator: **gemma3:4b**, 3.9B Q4_K_M with actual image projector. Digest `68ceab7e468a31c988b44d5a4984a0e21f58c4f7158c6ce29c1804babac38df7`.
- [Artist model blob integrity](runs/runtime/model-integrity.json), [evaluator blob integrity](runs/vision-provider-2026-11-24/model-integrity.json), [actual title-blind image-payload sanity request](runs/vision-provider-2026-11-24/sanity-request.json) and [raw evaluator response](runs/vision-provider-2026-11-24/sanity-response.raw.json).
- Source commits: forest `f0aa5ba64614d1ef5c0fcbc9a851e505ec96d1d8`; mountains `2db4f232ef6f2385375a79bd87c3df77501999ec`; sunflower/first dragon/first controls `3fc06f4777a68b492928d6a08a0dd251977af895`; title-visible pilot `ccd40b022cb1d6ad2646758f3ed53ac10de1b68f`; truncated-memory two-pass experiment `01090ba7c8c97855a7e3d352c3e9003e7278e972`; corrected retrieval run `bb7128d76a6c210d84234326576ef6bc7f1e2509`.

UTC timestamps, subject/source, model/provider/digest, attempt number, original model replies, self-critique, actual pixel reports, SVG/PNG hashes, journal tips and verification state are recorded per attempt. Later runs use unchanged worktrees. The first two sessions occurred while source was evolving; a Git SHA alone does not attest a clean working tree. Exact module hashes are retained where available.

## Reproduce through the existing Core

```sh
python -m pip install 'CairoSVG==2.8.2' 'drawsvg>=2,<3'
# Start Ollama and install the identified artist/evaluator models first.
BEAN_REASONING_PROVIDER=ollama BEAN_OLLAMA_MODEL=qwen2.5:3b \
python -m bean.creativity.sketch_lab --db drawing-core.sqlite3 \
  --out new-subject --task-ref original-subject --require-live \
  --attempts 2 --all-attempts --backend stdlib --seed 202611240 \
  --vision-model gemma3:4b
```

Omit `--subject` for model subject choice; provide it only for an explicitly human-assisted challenge. Missing providers and invalid images fail honestly. Existing run directories cannot be overwritten. Publication requires an exact-byte public-safe review manifest; the curator verifies receipts/hashes and rerenders SVG to check the linked preview. See [BEAN_SKETCH_LAB.md](../BEAN_SKETCH_LAB.md) for the complete file-review protocol and benchmark commands.

## Failures and corrections are evidence

- Two forest drafts repeated coordinate `260`; no picture was fabricated.
- The title-visible vision pilot overclaimed recognition. Both raw reports are retained.
- A 337-character description rejected a valid-looking model response before rendering. Its original failed cell has no replacement PNG. The parser now accepts descriptions up to 1000 characters, with regression coverage.
- The oldest-first memory prefix cut JSON and masked fresh feedback. Recency-aware whole-record projection and actual-input comparison guards now cover that failure.
- One posthoc host note was written prematurely, invalidated and corrected after actual image inspection. Original/correction hashes are retained in the audit archive. It was never used as BEAN's feedback.
- Historical live-Qwen runs [43387654264](https://github.com/danieloculus0-bot/BEAN/actions/runs/43387654264) and [43391019294](https://github.com/danieloculus0-bot/BEAN/actions/runs/43391019294) failed and produced no successful original art.

Relevant drawing regressions, real provider runs, artifact rerenders and Core journal checks are executed separately. Green mechanism tests do not establish artistic quality. Exact final-head CI, integration and published-file verification will be recorded with the final update.
