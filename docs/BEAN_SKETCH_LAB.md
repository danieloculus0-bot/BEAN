# BEAN sketch laboratory: live model drawing and retained evidence

SketchLab uses BEAN's existing Python Core `NativeReasoningService`, model
adapters, optional `WebResearchService`, and SQLite/SHA journal. A configured
model chooses a subject and generates geometric primitives; the renderer does
not choose a subject or supply geometry. This runtime is separate from the
hosted ChatGPT BEAN memory adapter.

## Run a genuine model

Install the test and preview dependencies in the Python environment running
Core. CairoSVG also needs the platform's Cairo library. `drawsvg` is optional
when selecting the stdlib SVG backend.

```bash
python -m pip install pytest "CairoSVG==2.8.2" "drawsvg>=2,<3"
```

Configure an existing BEAN provider. For example, start an intentionally
installed local Ollama server:

```bash
ollama serve
```

In another terminal, install the model and select BEAN's existing
sketch-specific Ollama adapter:

```bash
ollama pull qwen2.5:3b
export BEAN_REASONING_PROVIDER=ollama
export BEAN_OLLAMA_MODEL=qwen2.5:3b
export BEAN_OLLAMA_URL=http://127.0.0.1:11434

python -m bean.creativity.sketch_lab \
  --db sketch-memory.sqlite3 --out sketch-runs/session-01 \
  --task-ref original-session-01 --attempts 2 --all-attempts \
  --backend stdlib --require-live
```

The CLI also selects the existing `local_llamacpp`, `openrouter`, and `openai`
providers through `BEAN_REASONING_PROVIDER`; they require their existing BEAN
configuration. Drawing JSON must fit the adapter's response contract. A
provider name alone is insufficient evidence that inference succeeded.

`--require-live` rejects fixture and unknown providers. The Ollama path also
rejects injected synthetic transports and checks the serving `/api/tags`
identity/digest. The run records the actual model response identity. These
checks are execution provenance, not cryptographic authentication of an
arbitrary remote model server. There is no scripted fallback when inference
or validation fails.

Without `--subject`, BEAN's model chooses any subject. To supply only a subject,
add, for example, `--subject "a folding chair"`; the receipt marks this as
human-assisted subject choice, while geometry still comes from the model.
`--attempts` permits one to five attempts. `--all-attempts` preserves the entire
budget even if textual self-critique claims satisfaction. Use a fresh output
directory for every run: existing drafts and receipts cannot be overwritten.

For several autonomous sessions, reuse the same journal and choose new output
directories/task references. Inspect their actual subjects before claiming
distinct subjects; asking for novelty does not establish that it occurred.

Optional `--online --provider auto` allows up to two reference pages through
BEAN's existing research service. `auto` uses Wikipedia without a configured
`BRAVE_SEARCH_API_KEY`; it is not unrestricted internet search. Reference URLs
and source excerpts remain evidence, not instructions. No downloaded code or
model-produced Python is executed.

The optional SVG renderer is MIT-licensed
[drawsvg](https://github.com/cduck/drawsvg). The stdlib backend remains available.
Finite validated primitives are rendered to SVG, checked against the restricted
SVG subset, and rasterized locally by CairoSVG with `unsafe=False` into a
512×512 white-background PNG. Pillow decodes the PNG before its hash is
recorded. A failed rasterizer leaves an error and no claimed preview.

## What the evidence establishes

Each attempt retains `attempt_XX.svg` when valid, `attempt_XX.png` when rendered,
`attempt_XX.json`, and `attempt_XX.raw.json`. Raw records retain actual prompts,
responses and errors. `model_calls.json` includes subject planning and review
calls. `progress.json` exposes completed attempts while a run is active.
`run.json` binds run identity, timestamps, model/provider, source Git SHA,
runtime source-file hashes, memory condition and attempt sidecar/artifact
hashes. The existing Core journal records attempts and the completed or failed
run. SQLite remains the canonical persistent experience store. A Git SHA alone
does not describe uncommitted changes; retain runtime hashes and commit the
reviewed source used for reproducibility.

| Field or class | Meaning |
| --- | --- |
| `execution_mode=live_model` | A supported BEAN provider was selected; inspect model calls and failures to establish successful inference. |
| `subject_source=autonomous` / `human` | The model selected the subject / a human supplied it. Neither field grades originality. |
| `synthetic_fixture` | Scripted regression input, including the existing rocket examples. Never autonomous artwork. |
| `unverified` | Execution origin or outcome has insufficient evidence. |
| `attempt_failed_*` / `run_failed` | Preserved failure; do not count as a successful drawing. An SVG can exist even when a later review fails. |
| `verification_state=artifacts_verified` | SVG and decoded PNG exist and match recorded SHA-256 hashes. This verifies bytes, not recognition or quality. |
| `self_review` | Model review of its description and coordinates; the text model has not seen pixels. |
| `external_feedback.state=host_reported_pixel_review` | Identified human/vision feedback bound to the actual PNG hash. The file protocol does not authenticate its author independently. |
| `legacy_host_report_unverified` | Compatibility callback without PNG-hash binding; it cannot establish pixel inspection. |
| `independent_visual_verification=false` | Host reports and self-confidence are not promoted into independently authenticated evaluation. |

There is no model-weight update. More files, changed output, matching hashes,
or self-reported satisfaction do not establish retained learning. Review
private prompts, journals, raw responses, references and logs before export.

## Review the actual image and feed the next attempt

The pluggable `visual_judge(png_path, subject)` callback receives the rendered
PNG. A legitimate evaluator must inspect those pixels; comparing the subject
with the model's own description is not visual evaluation.

The CLI supports a separate evaluator through a local folder:

```bash
python -m bean.creativity.sketch_lab \
  --db sketch-memory.sqlite3 --out sketch-runs/reviewed-session \
  --task-ref reviewed-session --attempts 2 --all-attempts \
  --backend stdlib --require-live --review-dir sketch-reviews --review-wait 600
```

For each image, `FileVisionReviewer` writes
`sketch-reviews/<PNG_SHA256>.request.json`, containing its actual path, hash,
subject and timestamp. The separate evaluator opens that image, then writes
`<PNG_SHA256>.json` in the same folder. The following is a response template,
not an actual evaluation:

```json
{
  "image_sha256": "EXACT_SHA256_OF_INSPECTED_PNG",
  "kind": "vision_model",
  "evaluator": "ACTUAL_EVALUATOR_IDENTITY",
  "satisfactory": false,
  "feedback": "ACTUAL_PIXEL_OBSERVATIONS_AND_SUGGESTED_REVISION"
}
```

Use `kind=human` only for human evaluation. Optional `scores` map the metrics
`spatial_coherence`, `subject_recognition`, `composition` and `diversity` to
numbers from 0 to 4. State and apply a consistent rubric. Missing scores remain
unavailable, not zero. Reports are bounded and must match the PNG hash.
If no reviewer responds within the wait, evaluation is recorded unavailable.
The maximum wait is 600 seconds per attempt.

The next attempt receives prior primitives, internal critique and external
feedback separately. Supply feedback while the run is waiting to affect that
revision. Adding a file after completion does not retroactively change a run
or its journal.

## Memory, restart and matched held-out challenges

`adaptive` retrieves recent sketch trials from the existing journal, including
errors, self-review and external feedback, across processes. `none` supplies no
prior-session sketch memory. `frozen` supplies only a fixed JSON trial snapshot
through `--frozen-memory`. All three conditions retain their own records and
use the same within-run feedback mechanism. These controls isolate
prior-session memory; they do not disable iteration.

The benchmark freezes a digest-bound protocol, shares the training checkpoint
with adaptive/frozen arms, and runs each held-out challenge in a new Python
process. The no-memory arm starts with a fresh Core journal. Subjects are
human protocol challenges, not autonomous choices. Training and held-out
subjects must be distinct and disjoint. For example:

```bash
python - <<'PY'
import json
from pathlib import Path
from bean.creativity.drawing_benchmark import protocol
spec = protocol(["a folding chair", "a watering can"],
                ["a teapot", "a lighthouse", "a dragonfly"],
                seed=20261119, attempts=2)
Path("drawing-protocol.json").write_text(json.dumps(spec, indent=2) + "\n")
PY

python -m bean.creativity.drawing_benchmark \
  --protocol drawing-protocol.json --out drawing-benchmark \
  --review-dir benchmark-reviews --review-wait 600
```

The configured provider is inherited. Matched seeds currently require the
Ollama sketch provider. Subject, seed and attempt budget match across arms;
execution order rotates. Commands, stdout/stderr, return codes, failures,
snapshots, Core databases and receipts are retained. Optional `--baseline-db`
copies an explicitly supplied checkpoint; keep private state out of public
experiments.

`summary.json` reports image-bound external spatial-coherence, recognition and
composition scores, last-minus-first iteration quality, matched
adaptive-minus-control held-out differences, and usable matched comparison
counts. Missing legitimate reviews produce null. Paired comparisons require
matching model/provider/digest/source identities and complete attempt budgets.
Recompute the report with:

```bash
python -m bean.creativity.drawing_benchmark \
  --protocol drawing-protocol.json --out drawing-benchmark --summarize-only
```

Portfolio diversity needs a joint review of every final held-out PNG in an
arm. Supply `portfolio-review.<arm>.json` with schema
`bean.draw.portfolio_review.v1`, `kind`, `evaluator`, `feedback`, all final
`image_sha256s`, and a `diversity` score from 0 to 4. Per-image diversity ratings
and distinct file/subject counts alone do not establish portfolio diversity.
Small matched score differences describe this protocol only; they do not
authenticate evaluator independence, establish broad generalization, or prove
weight learning.

## Public gallery and fixture separation

The existing Pages viewer is
<https://danieloculus0-bot.github.io/BEAN/bean-draw/>. It separates live model
artifacts, unverified records and synthetic fixtures. Existing rocket SVGs
remain explicitly labeled scripted tests.

Before exporting artwork, inspect its actual image and every published file
for public safety. Create a review manifest with schema
`bean.draw.public-review.v1`, actual `reviewer`, UTC `reviewed_at_utc`,
`public_safe=true`, and `files` mapping each reviewed basename to its SHA-256.
Cover each SVG, PNG, attempt JSON and `run.json` exactly. Public safety review
is separate from quality evaluation. Then curate:

```bash
python scripts/build_bean_draw_gallery.py \
  --source sketch-runs/reviewed-session --site docs/bean-draw \
  --review public-review.json
```

The curator checks source hashes, SVG security, PNG decoding, run binding to
each attempt, required live provenance and public review. It copies immutable
artifacts, exact attempt/run receipts and the review record, and rechecks
previously indexed assets. `live_model_artifact_verified` describes provenance
and byte integrity, not independently verified recognition. Publication follows
normal reviewed Pages integration. Static Pages cannot write feedback into
the private Core journal.

`scripts/run_bean_draw_fixture.py` and the synthetic-mechanism workflow exercise
actual Core with scripted rocket replies; they verify mechanics only. The
separate manually dispatched open-model workflow provisions genuine
Ollama/Qwen on a disposable runner and archives evidence. It does not publish
unreviewed output into main.

## Preserved prior failures

The genuine Qwen run
[43387654264](https://github.com/danieloculus0-bot/BEAN/actions/runs/43387654264)
loaded `qwen2.5:3b`, digest
`357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`,
and selected a futuristic cityscape. All four attempts failed with `ValueError`;
**zero SVGs were produced**. Its artifact retains failure sidecars and Core
journal, but the old implementation discarded raw answers and precise errors.
The specific validation cause cannot be recovered from those receipts alone.

Run [43391019294](https://github.com/danieloculus0-bot/BEAN/actions/runs/43391019294)
failed model retrieval with HTTP 503 before drawing. Neither failed run
establishes successful original artwork. New raw/error retention makes future
failures diagnosable. This document does not claim a successful new live run
or an artistic learning improvement.

## Regression checks

```bash
python -m pytest bean/tests/test_sketch_lab.py \
  bean/tests/test_drawing_evidence.py bean/tests/test_bean_draw_gallery.py \
  bean/tests/test_drawing_benchmark.py -q -ra
```

These synthetic tests cover separate-process persistence, failures/iterations,
provider and transport rejection, preview creation/failure, feedback hashes,
SVG security, index integrity, public review binding and benchmark controls.
Passing them does not substitute for genuine inference or image inspection.

## BEAN CONTEXT ACK v1

Task: extend and execute the existing drawing pipeline with truthful evidence.
Existing systems checked: AGENTS, AI_GATEKEEPER, SOFTWARE_AUDIT_SKILL, canonical
origin, sketch PRs #327/#334/#336, reasoning/research services, journal, model
adapters, gallery and workflow failures above.
Confirmed assets reused: NativeReasoningService, WebResearchService,
ExperienceBank SHA journal, OllamaClient and the existing Pages gallery.
Ledger/scoreboard limits: historical scoreboards do not establish drawing
performance; matched drawing evidence requires the explicit protocol.
Current evidence: source/regression checks establish only tested mechanisms;
exact live results belong in separate run receipts.
Unknowns: independent visual authentication, broad retained-learning benefit
and generalization remain unproven by infrastructure alone.
Minimum change: retained provenance, previews, pluggable pixel review,
restart/control measurement and reviewed gallery export in existing Core.
Runtime/behavior-policy changes: no change to ordinary startup or effectors;
drawing remains an explicitly invoked experiment.
