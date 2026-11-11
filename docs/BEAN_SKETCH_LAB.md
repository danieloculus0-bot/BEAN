# BEAN sketch laboratory: subject choice, web references, retained trials

This experimental Python Core tool is NOT available through the hosted ChatGPT @BEAN adapter. It is not a vision model, not an image diffusion model, and not proof of independently learned drawing skill. It reuses BEAN's original model adapter, native web research, and SHA-chained SQLite journal.

## How to run

Install MIT-licensed drawsvg version 2 on the machine running BEAN:

    python -m pip install "drawsvg>=2,<3"

Start the already-configured BEAN local llama.cpp server or configure an existing model adapter (Ollama, OpenRouter or OpenAI). Then invoke:

    python -m bean.creativity.sketch_lab --out sketch_trials --attempts 3 --backend drawsvg

Give BEAN permission to search the public web for its own subject's references:

    python -m bean.creativity.sketch_lab --out sketch_trials --attempts 3 --online --provider auto

BEAN uses an actual model call to select ANY subject and its own search query. It uses at most two public pages through the existing WebResearchService, then generates black line art as finite SVG primitives. BEAN describes the drawing and reviews the coordinates, with up to five attempts.

The MIT renderer is https://github.com/cduck/drawsvg ; keep its source and license attribution, verify any cloned revision, and do not copy arbitrary code from online pages into BEAN. By default the stdlib SVG renderer is used if drawsvg is unavailable. No downloaded scripts or user-provided Python snippets are executed.

Broad general web search requires a locally configured BRAVE_SEARCH_API_KEY. Without that credential, BEAN's existing automatic provider searches Wikipedia, not the entire internet. References are retained as URLs and bounded excerpts in BEAN's existing source-linked journal.

## Measurement boundaries

Without a real visual evaluation component, BEAN cannot inspect a rendered SVG. Its self-critique only examines the coordinates and written description. Trials are labeled unverified regardless of self-confidence. An application may inject a separate visual_judge(path, subject) callback returning a dict with Boolean satisfactory and text feedback, after examining the actual image. Such a result is only host reported, not independently authenticated. Do not fake image recognition by comparing the subject to its own generated label.

The Core journal stores the original BEAN-selected subject, each attempt status, model/provider identity, SVG digest, reference URLs, self-critique, and host feedback. SVGs remain on the host filesystem. Model weights are NOT updated by this code. The current iterative prompt can learn from prior feedback within a run and preserve experiment evidence across restarts. Genuine generalization needs repeated real-model tests, an independent vision evaluator, and matched baseline comparisons before reward updates.

## BEAN CONTEXT ACK v1

Task: optional BEAN-controlled sketch generation with online resource discovery.
Existing systems checked: hosted @BEAN status/recall, BEAN Python Core README, docs/AI_GATEKEEPER.md, docs/SOFTWARE_AUDIT_SKILL.md, scripts/invoke_bean.py, bean/research/research_service.py, bean/learning/reasoning_service.py, and the existing experiment history.
Confirmed assets reused: NativeReasoningService, WebResearchService, ExperienceBank SHA journal, existing model provider adapters.
Ledger and scoreboard: historically identified; compressed scoreboard NOT replayed, because no learned-performance claim is made.
Evidence: GitHub Actions synthetic integration workflow in this patch, pending exact-head result; live local model and visual assessment NOT TESTED.
Unknown: model-produced sketch quality, real reference retrieval, local GPU/server reachability, vision assessment.
Minimum change: one optional sketch experiment and its regression tests, without a second model or memory system.
Runtime/behavior-policy changes: none to normal Core startup, effectors or autonomous network scheduling.
