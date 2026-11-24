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
| Sunset over a quiet beach, Contabo VPS | 2 | 2 SVG + 2 PNG | Qwen 7B chose the subject; image feedback reached revision, but host recognition fell from 1/4 to 0/4 |

The original 3B series produced three distinct **model-chosen subject labels** with SVG/PNG output; the Contabo 7B run adds a fourth. These labels do not establish recognizable depictions. The dragon pilot repeated a subject; it is not additional subject diversity. The artist's final selection is preserved even when visual inspection disagrees with its claims.

Original receipts: [forest failures](runs/2026-11-19/subject-1/run.json), [mountains](runs/2026-11-19/subject-2/run.json), [sunflowers](runs/2026-11-19/subject-3/run.json), [dragon](runs/2026-11-20/subject-4/run.json). [Posthoc sunflower review](runs/2026-11-19/posthoc-subject3.json) did not influence those drafts.

[Actual artifact/Core-journal verification](runs/runtime/verification.json) and [joint original-portfolio review](runs/runtime/portfolio-review.originals.json) distinguish byte integrity from low observed visual diversity. Every draft, failure and critique is retained. These are fresh public-safe drawing experiment journals; the owner's private checkpoints were not loaded or published.

## Controls, feedback and measured limits

1. [First matched benchmark](runs/benchmark-2026-11-20/README.md): eight genuine attempts, teapot training and sailboat held-out evaluation. Every file survived; all live visual-review requests timed out during a paused session. Original scores remain null. Separate posthoc host-model reviews were 1/0/1 in all conditions. They did not influence generation.
2. [Automatic-review pilot](runs/pilot-vision-2026-11-24/posthoc-audit.json): a real Gemma vision model received actual dragon PNGs. With the title visible it confidently described a dragon that this host reviewer could not recognize. Both false-positive reports remain intact. Subsequent review uses a title-blind actual-image pass followed by a target-aware actual-image pass, with dimension-wise minimum ratings and both raw reports retained. This reduces one source of priming; it does not make the evaluator a truth oracle.
3. [Two-pass matched benchmark and audit](runs/auto-vision-benchmark-2026-11-24/README.md): 14 genuine attempts, 13 SVG/PNG pairs and one retained validation failure. Its adaptive/frozen **learning-exposure comparison is invalid**: the old 2400-character oldest-first context prefix excluded fresh feedback. Actual prompts and responses were identical. Descriptive Gemma scores must not be interpreted as evidence for or against a retained-memory benefit. Independent host-model inspection still found poor subject recognition.
4. [Corrected retrieval benchmark](runs/recent-memory-benchmark-2026-11-24/README.md): **14 genuine attempts, 14 SVG/PNG pairs, 12 distinct PNG hashes**, with teapot training and umbrella/bicycle held-out challenges. Every cell ran in a fresh Core process. Exact prompts confirm that adaptive bicycle generation received saved umbrella feedback, frozen generation retained only teapot feedback, and no-memory generation received `[]`. Raw model primitives regenerate the exact SVG bytes; PNG pixels, receipts and all four SQLite/SHA journal chains passed the [independent file audit](runs/recent-memory-benchmark-2026-11-24/audit/integrity.json). The first adaptive/frozen held-out case is an expected matched baseline and is excluded from learning comparisons.

The corrected experiment has only **one eligible adaptive/frozen challenge**. Gemma reports bicycle differences of spatial coherence **0**, subject recognition **+1**, composition **+1** on its 0–4 scale. These are evaluator reports, not independently established improvement. [Actual-image host inspection of all 14 attempts](runs/recent-memory-benchmark-2026-11-24/audit/final-visual-review.json) found no recognizable final teapot, umbrella or bicycle, and no final recognition advantage over either control. The adaptive first bicycle draft had weak wheel cues that its revision lost. Saved feedback delivery now works; retained-learning and generalization benefits remain unproven. Higher Gemma scores overstate recognition on these images.

5. [Actual Contabo VPS pilot](runs/vps-pilot-2026-11-24/README.md): the existing SketchLab CLI ran with real **qwen2.5:7b**, independently chose **“A Sunset Over a Quiet Beach”**, and produced two original SVG/PNG drafts. The existing local model service was reused. Gemma received each actual image twice, and its first feedback text and image hash reached both the planning and drawing prompts for attempt 2. Exact primitive replay, PNG pixels, receipts, model-blob verification records and a separate three-event Core journal backup are retained. The title describes BEAN's intended subject; the final image did not clearly depict it. Gemma described unrelated objects while assigning nonzero subject scores, and both contradictory reports remain unchanged. The host observer rated recognition 1/4 then 0/4. This is genuine VPS execution, **not demonstrated improvement**. The larger artist, changed provider version and new host were not matched controls for learning. This old-source CLI run does not validate the later orchestrator adapter patch in PR #513.

All experiments keep `weights_updated=false` and `learning_improvement_verified=false`. Changed geometry, more files, self-satisfaction and higher model scores do not establish learning. Human aesthetic evaluation is unavailable. External Codex/Gemma observations are model reports, not authenticated ground truth.

## Runtime and source provenance

- Original artist: Ollama **0.40.16**, **qwen2.5:3b**, 3.1B Q4_K_M, CPU. Model digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
- Contabo artist: Ollama **0.40.18**, **qwen2.5:7b**, 7.6B Q4_K_M, CPU. Model digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`. [Actual launch command and source](runs/vps-pilot-2026-11-24/launch-receipt.json), [model verification receipt](runs/vps-pilot-2026-11-24/original/provider-integrity.json), [rendered attempts and full evidence](runs/vps-pilot-2026-11-24/README.md).
- Automatic evaluator: **gemma3:4b**, 3.9B Q4_K_M with actual image projector. Digest `68ceab7e468a31c988b44d5a4984a0e21f58c4f7158c6ce29c1804babac38df7`.
- [Artist model blob integrity](runs/runtime/model-integrity.json), [evaluator blob integrity](runs/vision-provider-2026-11-24/model-integrity.json), [actual title-blind image-payload sanity request](runs/vision-provider-2026-11-24/sanity-request.json) and [raw evaluator response](runs/vision-provider-2026-11-24/sanity-response.raw.json).
- Source commits: forest `f0aa5ba64614d1ef5c0fcbc9a851e505ec96d1d8`; mountains `2db4f232ef6f2385375a79bd87c3df77501999ec`; sunflower/first dragon/first controls `3fc06f4777a68b492928d6a08a0dd251977af895`; title-visible pilot `ccd40b022cb1d6ad2646758f3ed53ac10de1b68f`; truncated-memory two-pass experiment `01090ba7c8c97855a7e3d352c3e9003e7278e972`; corrected retrieval run `bb7128d76a6c210d84234326576ef6bc7f1e2509`.

UTC timestamps, subject/source, model/provider/digest, attempt number, original model replies, self-critique, actual pixel reports, SVG/PNG hashes, journal tips and verification state are recorded per attempt. Later runs use unchanged worktrees. The first two sessions occurred while source was evolving; a Git SHA alone does not attest a clean working tree. Exact module hashes are retained where available.

The Contabo CLI source was `54b0a4d2c17face7ffbf3d016ef348c5a055164a`; its four recorded module hashes match that revision. Its fresh public drawing journal is separate from the primary service's private memory. An initial exporter withheld the journal because it missed the legitimate run-completion event; that omission is preserved alongside the later bounded verification of two draft events and one completion event. No drawing was regenerated to correct the exporter.

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

The corrected experiment was executed from unchanged source `bb7128d76a6c210d84234326576ef6bc7f1e2509` with this preregistered protocol (use a new output directory):

```sh
BEAN_REASONING_PROVIDER=ollama BEAN_OLLAMA_MODEL=qwen2.5:3b \
python -m bean.creativity.drawing_benchmark \
  --protocol docs/bean-draw/runs/recent-memory-benchmark-2026-11-24/original/protocol.json \
  --out new-recent-memory-benchmark --vision-model gemma3:4b
```

The archived [execution receipt](runs/recent-memory-benchmark-2026-11-24/original/execution.json) preserves every original per-cell command, budget and seed. The protocol SHA-256 is `85fef0d10c79300b4ee4cec3d0ff93a9ffce324d53282b7272826a6508a41ff7`. The human-selected benchmark subjects are separate from BEAN's model-chosen gallery subjects.

## Failures and corrections are evidence

- Two forest drafts repeated coordinate `260`; no picture was fabricated.
- The title-visible vision pilot overclaimed recognition. Both raw reports are retained.
- A 337-character description rejected a valid-looking model response before rendering. Its original failed cell has no replacement PNG. The parser now accepts descriptions up to 1000 characters, with regression coverage.
- The oldest-first memory prefix cut JSON and masked fresh feedback. Recency-aware whole-record projection and actual-input comparison guards now cover that failure.
- One posthoc host note was written prematurely, invalidated and corrected after actual image inspection. Original/correction hashes are retained in the audit archive. It was never used as BEAN's feedback.
- Historical live-Qwen runs [43387654264](https://github.com/danieloculus0-bot/BEAN/actions/runs/43387654264) and [43391019294](https://github.com/danieloculus0-bot/BEAN/actions/runs/43391019294) failed and produced no successful original art.

Relevant drawing regressions, real provider runs, artifact rerenders and Core journal checks are executed separately. The local browser check verified eight live-model cards, two separately filtered fixtures, working receipt links, no JavaScript errors and a layout that fits a 390-pixel viewport. A separate HTTP check matched 75 gallery, image and receipt files against their reviewed repository bytes. These checks establish display and artifact integrity, not artistic quality.

[PR #510](https://github.com/danieloculus0-bot/BEAN/pull/510) records exact-head CI and integration status. Reproduce the drawing regression checks with:

```sh
python -m pytest bean/tests/test_sketch_lab.py \
  bean/tests/test_bean_draw_gallery.py bean/tests/test_drawing_evidence.py \
  bean/tests/test_drawing_benchmark.py bean/tests/test_vision_drawing_review.py \
  bean/tests/test_drawing_memory_context.py -q -ra
```

The gallery now labels each live entry with **intended subject** and **attempt number**. A title records what the model set out to draw. Pixel review assesses what the resulting image actually depicts. [PR #513](https://github.com/danieloculus0-bot/BEAN/pull/513) records the later adapter, label and Contabo evidence integration. Green mechanism tests do not establish artistic quality or retained learning. Original source SHAs remain pinned above even after integration.
