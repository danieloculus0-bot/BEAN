# BEAN

**[BEAN Workshop — Projects and demonstrations](https://danieloculus0-bot.github.io/BEAN/portfolio/)** · Browse 19 catalogued projects and nine featured browser experiences, with published source code, development status and available test evidence.

Persistent experimental reasoning and evidence system. BEAN Core maintains SQLite-backed observations, source-aware claims, revision history, recovery and repeatable research tests. It is not a production-grade autonomous software engineer.

## Current Python Core status (October 25, 2026)

**Implemented in Core:** one native reasoning service with BEAN-owned SQLite/SHA memory, source-linked error reflection, reusable procedures, measured contextual strategy choice, real-model provider adapters, Q-learning, neural checkpoint recovery, and host-reported positive/negative outcome receipts. Merged PRs #170–#179 recovered formerly isolated cognition and research. Software tests demonstrate interfaces, not general intelligence.

**Judgment and counsel:** The [knowledge sufficiency policy](docs/BEAN_JUDGMENT_POLICY_2026-10-25.md) can prefer an adequate existing answer, select supported expert counsel, defer on insufficient evidence, or investigate when reliable guidance is unavailable. It reuses the current native reasoning inbox and SHA journal, not another brain. Source expertise and confidence are host-attested rather than independently authenticated; judgment feedback persists but does not yet retrain trust or model weights. This policy is a new Core integration with unit/CI acceptance, not independently validated expertise.

**Still unproven or not automatically connected:** general intelligence, independent cross-domain transfer, real-world expert authentication, autonomous truth grading, production deployment, trading profitability, and full synchronization of the hosted connector, Bridge, AIscend and Axiom. GitHub source integration alone does not imply those applications invoke every Core capability.

For reproducible evidence and boundaries see the [native reasoning contract](docs/BEAN_NATIVE_REASONING_CORE_2026-10-25.md), [mainline audit](docs/BEAN_MAINLINE_CONSOLIDATION_AUDIT_2026-10-25.md), and [judgment policy](docs/BEAN_JUDGMENT_POLICY_2026-10-25.md).

## Featured application: EZ-Office (October 22, 2026)

**[Launch the EZ-Office suite in the Workshop](https://danieloculus0-bot.github.io/BEAN/portfolio/ez-office/)** · [Standalone source and automated tests](https://github.com/danieloculus0-bot/EZ-Office)

EZ-Office is a **working offline-first HTML/JavaScript productivity suite**. Writer formats text and exports actual DOCX, HTML, or TXT; Sheets recalculates formulas and exports XLSX/CSV; Slides adds images, audio, video, themes and PPTX/native multimedia output; Media saves original files or PNG frames; Mail handles EML drafts and optional Google Gmail / Microsoft Outlook provider connections. Documents and presentations can use browser Print / Save as PDF. Five tools share one interface with on-demand loading and cleanup when switching.

**Buildout pass 01 (October 22, 2026):** Added Writer find/replace, Sheets multi-cell clipboard paste and cell navigation, a slide navigator and notes export, Media speed/loop controls and metadata, local EML reopening, and an unsaved-tab-close warning. See the [functionality/deployability audit](https://github.com/danieloculus0-bot/EZ-Office/blob/main/docs/BUILDOUT_AUDIT.md) for verification gates and remaining gaps.

**Native media validation, pass 03 (October 22, 2026):** EZ Media now has native Play/Pause, seeking, responsive inline video, metadata and codec-error feedback. A required browser test generates real video/audio files and verifies decoded video frames, audio timelines, slide-embedded playback and file cleanup. WebM/MP3/WAV played in both Chromium/WebKit Linux test builds; H.264/AAC MP4 played in WebKit but was not advertised by Chromium's test build. No extra player, plugin, transcoder or JavaScript codec package is shipped. See [media compatibility and venvWin requirements](https://github.com/danieloculus0-bot/EZ-Office/blob/main/docs/MEDIA_COMPATIBILITY.md).

**Buildout pass 02 (October 22, 2026):** Added bounded offline import for Word DOCX paragraphs and the first Excel XLSX worksheet, along with view-only Sheets sort/filter, evaluated visible CSV and complete small-sheet Print/PDF. PPTX output now preserves paragraph breaks and alignment. Import ZIP size, integrity and compressed-file round-trips are browser-tested.

The Workshop hosts a pinned copy of the actual application, not a fake dashboard. Basic DOCX/XLSX/PPTX **export** and limited DOCX/XLSX **import** are working and covered by structural/browser tests. Complex Office formatting, native PPTX import, full Office compatibility and host-RAM savings are **not** established. Gmail/Outlook connect only after registering an OAuth public client and authorizing the mail scopes. This is separate from BEAN Core. Read the [EZ-Office README](https://github.com/danieloculus0-bot/EZ-Office/blob/main/README.md) for exact scope. EZ-Office is a separate project from BEAN Core and Axiom.

## Consolidated Core and request-handling audit (October 25, 2026)

The [BEAN mainline consolidation and code audit](docs/BEAN_MAINLINE_CONSOLIDATION_AUDIT_2026-10-25.md) identifies real implementations, merged PRs, repaired request/learning defects and remaining cross-app work. **Merged PRs #170–#179** include the native reasoning runtime, Nemotron research, restored cognition blocks, source-level software audit, evidence-linked positive/negative feedback, unique inference receipts, optimized journal append and recovered Bridge research. Old stacked drafts #100, #131, #132, #144 and #167–#169 were closed as superseded **without deleting their original experiment branches or failures**. Legacy #8 and the separate local-MCP connection #115 remain tracked for reconciliation with the current Core rather than blindly importing obsolete or competing memory code.

## BEAN Core ⇄ Bridge closed-loop reasoning feedback (October 25, 2026)

[Merged PR #180](https://github.com/danieloculus0-bot/BEAN/pull/180) connects a real selected-strategy inference receipt to **BEAN AI Bridge's existing two-origin evidence investigation**, then records accepted, source-linked corrections in the **same Core reasoning ledger**. [PR #181](https://github.com/danieloculus0-bot/BEAN/pull/181) scopes Bridge-derived case-specific lessons to their original concepts, preventing unrelated sensors with similar vocabulary from inheriting a false source claim. This is an opt-in Python/host integration through `BridgeReasoningLoop` and `register_bridge_feedback_handler`; a trusted source verifier must be supplied by the host, not arbitrarily declared in client JSON.

**Reproduced synthetic mechanism results:** frozen-model holdout 2/2 after evidence-backed correction versus 0/2 cold and 0/2 irrelevant-memory control, with both Windows and Ubuntu regression checks passing. Negative tests reject single origin, conflicting records, unchecked observations and cross-concept memory bleed. These tests demonstrate feedback/retrieval wiring, not general model-weight learning. [Integration and adversarial protocol](docs/BEAN_BRIDGE_REASONING_FEEDBACK_2026-10-25.md).

## BEAN-owned reasoning and learning selection (October 25, 2026)

BEAN Core now has an **optional, integrated native reasoning service** that connects model-generated candidate rules, source-linked reflections, reusable skills, measured strategy comparisons, frozen future decisions and actual provider inference through **one persistent BEAN-owned SHA-chain journal**. This is not a separate agent framework or replacement memory database. The same BEAN service backs local inbox commands and direct Python calls; it can use pinned free Nemotron via OpenRouter or other configured reasoning adapters without surrendering memory or learned decisions to a model vendor.

**Mainline publication status (October 25, 2026):** [PR #170](https://github.com/danieloculus0-bot/BEAN/pull/170) actually merged BEAN-owned rule generation, memory, measured strategy selection and real-provider reasoning into the ordinary Python Core startup and inbox. [PR #171](https://github.com/danieloculus0-bot/BEAN/pull/171) subsequently merged the *working experimental* Nemotron real-model tests and rule-derivation research utilities into `bean/evaluation/`, plus [their original success, error, and artifact provenance](docs/BEAN_REASONING_RESEARCH_MAINLINE_2026-10-25.md). [PR #172](https://github.com/danieloculus0-bot/BEAN/pull/172) also promoted cognition/curiosity code. A module that is **merged and available for development** is not thereby proven on the user's Python desktop; full automatic live-provider learning, real-world transfer and the hosted/AIscend connection remain work to test and repair on main, **not reasons to quarantine promising source indefinitely**.

**On every normal Python Core startup**, BEAN initializes a persistent native reasoning ledger beside its existing SQLite memory. Override the path with `BEAN_REASONING_LESSONS_DB` or explicitly disable it with `BEAN_REASONING_ENABLED=0`. Optional inference uses `BEAN_REASONING_PROVIDER=openrouter` with `OPENROUTER_API_KEY`, `openai`, or `ollama`. See the [Core reasoning integration contract](docs/BEAN_NATIVE_REASONING_CORE_2026-10-25.md). Without a configured provider, BEAN still remembers and selects strategies but **cannot generate a real model answer**; it does not silently simulate one. The optional Bridge adapter now invokes this Core service **when a trusted host installs its verifier**; hosted BEAN notes, Axiom and AIscend remain separate and are not silently synchronized. **General cognitive transfer, independently authenticated rewards, and real-market profitability remain unproven.**

## Integrated Core Q-learning (October 22, 2026)

**[Merged integration PR #153](https://github.com/danieloculus0-bot/BEAN/pull/153)** brings the original tested SpongeTD Q-learning, exact compressed/recoverable Q-value checkpoints, SpongeIntuition controller and Lab027 benchmark into Python BEAN Core. A [real local learning runtime](bean/learning/runtime.py) now accepts host-observed outcomes and updates the Q table through `learning_choose`, `learning_feedback`, `learning_checkpoint`, and `learning_status` in BEAN's existing command inbox. Configure `BEAN_LEARNING_DB` and see the [integration contract](docs/BEAN_LEARNING_CORE_INTEGRATION_2026-10-22.md) for use and limitations.

The integration passed [Windows/Ubuntu learning CI](https://github.com/danieloculus0-bot/BEAN/actions/runs/39865857319) and [the four-job full Core regression matrix](https://github.com/danieloculus0-bot/BEAN/actions/runs/39865857419) at PR head `15ba3357`. Source-identical Lab027 files also match the experimentally tested blob hashes at `4d969b0e`. **This is actual tabular reinforcement learning in the local Python runtime, not a live hosted connector, autonomous reward collection, LLM weight training, or proof of general cross-domain intelligence.** Uncheckpointed updates are not durable; reward and validation values are host-reported.

## Measured outcome rewards and durable learning (October 22, 2026)

[**Merged PR #154**](https://github.com/danieloculus0-bot/BEAN/pull/154) promotes the existing signed-reward scoring contract and connects it to the real local Q learner. Complete, matched evaluator reports now feed signed Q updates, so observed regressions reduce learned action values and improvements increase them. The `learning_evaluated_feedback` inbox command stores each uniquely identified reward receipt and its Q checkpoint **in one SQLite transaction**; `learning_reward_history` retrieves prior observations and source links. Duplicates, incomplete comparisons, and fewer than 30 matched cases do not mint learning credit.

[**Feedback integration CI**](https://github.com/danieloculus0-bot/BEAN/actions/runs/39867858101) passed on Windows and Ubuntu, Python 3.10 and 3.12, including Core regressions. See [the exact feedback API and limitations](docs/BEAN_MEASURED_FEEDBACK_2026-10-22.md).

**Evidence boundary:** the evaluator values, URL, and receipt hash are supplied by the calling application, **not independently authenticated by BEAN**. The general reasoning engine still produces ungraded proposals requiring review; it is **not** autonomously rewarding itself. The hosted BEAN memory connector and separate BEAN applications have not been wired to this local evaluator interface.

## BEAN-native reasoning and measured intuition (October 21, 2026)

- **[Workshop learning-results page](https://danieloculus0-bot.github.io/BEAN/portfolio/bean-learning/)**: mobile-friendly walkthrough of what was actually tested, with direct links to code, CI and evidence.
- **[Lab026 original research PR #144](https://github.com/danieloculus0-bot/BEAN/pull/144)**: retained for historical development evidence; its reusable source-linked recall, error reflection, procedures and strategy selection have now been **promoted into Core main** via [PR #170](https://github.com/danieloculus0-bot/BEAN/pull/170).
- **[Lab027 reinforcement-learning evaluation (draft PR #149)](https://github.com/danieloculus0-bot/BEAN/pull/149)**: real original SpongeTD Q-learning on 3,000 synthetic training puzzles, a separate 180-map tuning set, and **240 untouched holdout layouts**. Trained Q-learning with the same loop-avoidance controller solved 237/240 maps versus 232/240 for cold Q; mean moves were 21.7 versus 69.0. Exact Q-values survived checkpoint/restart.
- **[Verified Lab027 GitHub CI run](https://github.com/danieloculus0-bot/BEAN/actions/runs/39550106061)**: both Windows and Ubuntu succeeded on evaluated code revision `4d969b0e`, with inspectable compressed event-ledger artifacts.

These experiments demonstrate task-family learning and reusable mechanisms, **not** general intelligence, production deployment, external action authority or neural training. Lab026 and the broader Lab027 research PRs remain separate experiments; the source-identical tabular learner and its held-out tests were promoted to Python Core through PR #153. The newest changes on other draft branches may be newer than their listed successful CI revisions.

## Before any BEAN engineering work

**AI contributors: [Read and acknowledge the BEAN activity gatekeeper](docs/AI_GATEKEEPER.md)** (also referenced by [`AGENTS.md`](AGENTS.md)). Check connected BEAN memory where available, inventory existing branches/PRs and their CI, and read the compressed ledger before designing or modifying anything. This is a context-and-evidence gate, not a new runtime behavioral filter.

## Already-built learning infrastructure

- [**SpongeTD tabular Q-learning in Core main**](bean/optimization/sponge_td.py): real temporal-difference updates and scored, recoverable Q-value memory, with [reproducible held-out maze benchmark](bean/optimization/intuition_maze.py). The earlier [Breakout holdout ledger](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-sponge-core-20261011/experiments/sponge_breakout/evidence/score_ledger.jsonl) remains on its research branch.
- [**SpongeDQN neural Q-network**](bean/optimization/sponge_dqn.py): experimental PyTorch 3→64→64→3 network with minibatch replay, target network, real gradient training and compressed neural checkpoint restoration. [Matched tabular/DQN/cold evaluation](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-deep-q-learning-20261012/experiments/sponge_breakout/deep_trial.py) is game-specific, not general neural recall or production runtime.
- [**Neural evolution**](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-deep-q-learning-20261012/experiments/sponge_breakout/evolve.py): candidate inheritance and mutation; trials include important regressions, not a replicated overall gain.
- [**Persistent compressed scoring ledger**](https://github.com/danieloculus0-bot/BEAN/tree/experiment/anticipatory-ledger-20261020/research/persistent_ledger): append-only historical evidence with small rebuildable scoring summaries.
- [**BEAN tests BEAN**](https://github.com/danieloculus0-bot/BEAN/pull/140): research-only indexed JUnit test retrieval, comparing verified options through the existing Core selector; neural retrieval training is *not* implemented.
- [**BEAN Bridge Lab009**](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/46): revised frozen-replay versus online-acquisition scoring (0/3 baseline, 2/3 after restart without new evidence, 3/3 after new synthetic research).
- [**BEAN-readable scoreboard and reward**](https://github.com/danieloculus0-bot/BEAN/pull/141): experimental JSON scoreboard context, signed reward for matched improvement/regression, and duplicate evaluation-credit detection. Not yet consumed automatically by the hosted BEAN connector or neural DQN.

Some assets above remain **distinct research branches and draft PRs**; SpongeTD and its local runtime now exist in Core `main`. Consult [the public learning page](https://danieloculus0-bot.github.io/BEAN/#learning) and exact linked test receipts. All neural claims remain limited to controlled synthetic experiments.

## Current build state

**Reviewed:** 2026-10-22 · **Merged learning Core:** `a9c945b19e11` · **Type:** working experimental/beta code; not automatically production-certified.

- [BEAN AIscend public demo checks](https://github.com/danieloculus0-bot/BEAN/actions/runs/39503225654) — **Passed** on an earlier `main` revision; the static demo has a separate check.
- [BEAN full Core regression](https://github.com/danieloculus0-bot/BEAN/actions/runs/39865857419) — **Passed** across Windows/Linux and Python 3.10/3.12 at integration PR head; merge includes the unchanged tested files.
- [BEAN learning integration](https://github.com/danieloculus0-bot/BEAN/actions/runs/39865857319) — **Passed** across Windows and Ubuntu, including 3,000-episode Lab027 evaluation.
- [Pages build and deployment](https://github.com/danieloculus0-bot/BEAN/actions/runs/39512878048) — **Passed** at inspected `main`.

[See live Actions](https://github.com/danieloculus0-bot/BEAN/actions) for newer results; this is a dated evidence snapshot, not a continuously updated indicator.

## Implemented today

- Persistent memory, source/contradiction tracking and offline replay backed by runnable Core code.
- Local Python Q-learning and reward feedback with explicit checkpoint persistence through the runtime inbox.
- Experimental local model/Ollama and voice integrations, with host-neutral reasoning interfaces.
- Public [BEAN laboratory](https://danieloculus0-bot.github.io/BEAN/) and the shared charcoal/electric-lime interface.

## Verify BEAN Core locally

Start with [Getting Started](docs/GETTING_STARTED.md), the [offline verification guide](docs/VERIFIED_UTILITY_AND_EVIDENCE_2026-10-11.md), and the executable test examples in `bean/tests/`. Review each lab's own acceptance criteria rather than assuming every experiment is deployed.

## Branch-specific research results

Earlier Lab026/Bridge research ran on separate branches, including a historical `ezbean` import failure. Its useful reasoning, learning and Bridge adapter components were subsequently consolidated into Core `main` through PRs #170–#179. Original experiment archives and failures remain linked for provenance; real-world cross-application operation and general transfer remain open acceptance tasks.

The public AIscend browser demo is a read-only simulation, not a live wallet/trading or private account connector. BEAN's public website and real local Ollama Core are different runtime surfaces.

## Known boundaries

- Autonomous code-author/self-repair attempts have had failing independent validation. A rejected candidate is not a successful autonomous repair.
- BEAN Core, [BEAN AI Bridge](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-) and [AIscend](https://github.com/danieloculus0-bot/AIscend) are different runtimes; a trading/execution feature in an application does not belong to Core.
- Repository source is viewable; no general redistribution license has been established. Do not infer open-source licensing from the public repository.

## Next engineering work

Connect real host evidence and reviewer authentication to Core judgments, measure when existing counsel versus independent exploration actually helped, and calibrate source reliability on independently graded held-out tasks. Integrate Bridge, AIscend and hosted BEAN using authenticated Core adapters rather than parallel memories. Reproduce gains across unrelated domains before claiming generality.

## Documentation

- [BEAN site](https://danieloculus0-bot.github.io/BEAN/)
- [Research and verification docs](docs/experimental-research-index-2026-10.md)
- [Local Q-learning integration contract](docs/BEAN_LEARNING_CORE_INTEGRATION_2026-10-22.md)
- [**Complete prior README, including history and detailed instructions**](docs/archive/README_2026-10-20_before_refresh.md)

Historical experiments, dated reports and superseded architectural claims have been moved out of this landing page, **not deleted**.
