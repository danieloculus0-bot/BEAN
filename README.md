# BEAN

**[BEAN Workshop — Projects and demonstrations](https://danieloculus0-bot.github.io/BEAN/portfolio/)** · Browse 19 catalogued projects and nine featured browser experiences, with published source code, development status and available test evidence.

Persistent experimental reasoning and evidence system. BEAN Core maintains SQLite-backed observations, source-aware claims, revision history, recovery and repeatable research tests. It is not a production-grade autonomous software engineer.

## Featured application: EZ-Office (October 22, 2026)

**[Launch the EZ-Office suite in the Workshop](https://danieloculus0-bot.github.io/BEAN/portfolio/ez-office/)** · [Standalone source and automated tests](https://github.com/danieloculus0-bot/EZ-Office)

EZ-Office is a **working offline-first HTML/JavaScript office experiment**: Writer edits TXT/Markdown; Sheets imports/exports CSV; Slides presents text-based decks; Media opens browser-supported local audio/video/images; and Mail exports `.eml` drafts or hands off to a configured mail program. Five tools share one interface with on-demand loading and cleanup when switching. No login, cloud service, or separate application server is necessary for these functions.

The Workshop serves a pinned copy of the working application. It does **not** imply BEAN AI runs inside EZ-Office, that native DOCX/XLSX/PPTX documents are compatible, that mail accounts can synchronize, or that host-RAM savings were measured. Read the [EZ-Office README](https://github.com/danieloculus0-bot/EZ-Office/blob/main/README.md) for exact scope. EZ-Office is a separate project from BEAN Core and Axiom.

## Integrated Core Q-learning (October 22, 2026)

**[Merged integration PR #153](https://github.com/danieloculus0-bot/BEAN/pull/153)** brings the original tested SpongeTD Q-learning, exact compressed/recoverable Q-value checkpoints, SpongeIntuition controller and Lab027 benchmark into Python BEAN Core. A [real local learning runtime](bean/learning/runtime.py) now accepts host-observed outcomes and updates the Q table through `learning_choose`, `learning_feedback`, `learning_checkpoint`, and `learning_status` in BEAN's existing command inbox. Configure `BEAN_LEARNING_DB` and see the [integration contract](docs/BEAN_LEARNING_CORE_INTEGRATION_2026-10-22.md) for use and limitations.

The integration passed [Windows/Ubuntu learning CI](https://github.com/danieloculus0-bot/BEAN/actions/runs/39865857319) and [the four-job full Core regression matrix](https://github.com/danieloculus0-bot/BEAN/actions/runs/39865857419) at PR head `15ba3357`. Source-identical Lab027 files also match the experimentally tested blob hashes at `4d969b0e`. **This is actual tabular reinforcement learning in the local Python runtime, not a live hosted connector, autonomous reward collection, LLM weight training, or proof of general cross-domain intelligence.** Uncheckpointed updates are not durable; reward and validation values are host-reported.

## BEAN-native reasoning and measured intuition (October 21, 2026)

- **[Workshop learning-results page](https://danieloculus0-bot.github.io/BEAN/portfolio/bean-learning/)**: mobile-friendly walkthrough of what was actually tested, with direct links to code, CI and evidence.
- **[Lab026 reasoning skills (draft PR #144)](https://github.com/danieloculus0-bot/BEAN/pull/144)**: source-linked experience recall, reflection on errors, reusable procedures, and controlled strategy selection using BEAN's existing SQLite Journal.
- **[Lab027 reinforcement-learning evaluation (draft PR #149)](https://github.com/danieloculus0-bot/BEAN/pull/149)**: real original SpongeTD Q-learning on 3,000 synthetic training puzzles, a separate 180-map tuning set, and **240 untouched holdout layouts**. Trained Q-learning with the same loop-avoidance controller solved 237/240 maps versus 232/240 for cold Q; mean moves were 21.7 versus 69.0. Exact Q-values survived checkpoint/restart.
- **[Verified Lab027 GitHub CI run](https://github.com/danieloculus0-bot/BEAN/actions/runs/39550106061)**: both Windows and Ubuntu succeeded on evaluated code revision `4d969b0e`, with inspectable compressed event-ledger artifacts.

These experiments demonstrate task-family learning and reusable mechanisms, **not** general intelligence, production deployment, external action authority or neural training. Lab026 and the broader Lab027 research PRs remain separate experiments; the source-identical tabular learner and its held-out tests were promoted to Python Core through PR #153. The newest changes on other draft branches may be newer than their listed successful CI revisions.

## Before any BEAN engineering work

**AI contributors: [Read and acknowledge the BEAN activity gatekeeper](docs/AI_GATEKEEPER.md)** (also referenced by [`AGENTS.md`](AGENTS.md)). Check connected BEAN memory where available, inventory existing branches/PRs and their CI, and read the compressed ledger before designing or modifying anything. This is a context-and-evidence gate, not a new runtime behavioral filter.

## Already-built learning infrastructure

- [**SpongeTD tabular Q-learning in Core main**](bean/optimization/sponge_td.py): real temporal-difference updates and scored, recoverable Q-value memory, with [reproducible held-out maze benchmark](bean/optimization/intuition_maze.py). The earlier [Breakout holdout ledger](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-sponge-core-20261011/experiments/sponge_breakout/evidence/score_ledger.jsonl) remains on its research branch.
- [**SpongeDQN neural Q-network**](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-deep-q-learning-20261012/bean/optimization/sponge_dqn.py): experimental PyTorch 3→64→64→3 network with minibatch replay, target network, real gradient training and compressed neural checkpoint restoration. [Matched tabular/DQN/cold evaluation](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-deep-q-learning-20261012/experiments/sponge_breakout/deep_trial.py) is game-specific, not general neural recall or production runtime.
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

Adaptive Bridge/Lab026 PR experiments are separate from the stable Core mainline. A recent experimental PR run failed during test collection because its new test imported `ezbean` without the BEAN AI Bridge dependency available in that CI job ([experimental failure](https://github.com/danieloculus0-bot/BEAN/actions/runs/39515571850)). This does **not** negate the successful Core `main` matrix. When the experiment is proposed for merge, its Bridge checkout/import and dedicated holdout tests must be included explicitly.

The public AIscend browser demo is a read-only simulation, not a live wallet/trading or private account connector. BEAN's public website and real local Ollama Core are different runtime surfaces.

## Known boundaries

- Autonomous code-author/self-repair attempts have had failing independent validation. A rejected candidate is not a successful autonomous repair.
- BEAN Core, [BEAN AI Bridge](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-) and [AIscend](https://github.com/danieloculus0-bot/AIscend) are different runtimes; a trading/execution feature in an application does not belong to Core.
- Repository source is viewable; no general redistribution license has been established. Do not infer open-source licensing from the public repository.

## Next engineering work

Connect measured observations and reward sources from real BEAN modules, persist evidence for every feedback event, and separately integrate the hosted connector and Bridge. Reproduce gains on independent holdout tasks rather than assuming one synthetic puzzle family generalizes.

## Documentation

- [BEAN site](https://danieloculus0-bot.github.io/BEAN/)
- [Research and verification docs](docs/experimental-research-index-2026-10.md)
- [Local Q-learning integration contract](docs/BEAN_LEARNING_CORE_INTEGRATION_2026-10-22.md)
- [**Complete prior README, including history and detailed instructions**](docs/archive/README_2026-10-20_before_refresh.md)

Historical experiments, dated reports and superseded architectural claims have been moved out of this landing page, **not deleted**.
