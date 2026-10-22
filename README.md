# BEAN

**[BEAN Workshop — Projects and demonstrations](https://danieloculus0-bot.github.io/BEAN/portfolio/)** · Browse 19 catalogued projects and nine featured browser experiences, with published source code, development status and available test evidence.

Persistent experimental reasoning and evidence system. BEAN Core maintains SQLite-backed observations, source-aware claims, revision history, recovery and repeatable research tests. It is not a production-grade autonomous software engineer.

## Featured application: EZ-Office (October 22, 2026)

**[Launch the EZ-Office suite in the Workshop](https://danieloculus0-bot.github.io/BEAN/portfolio/ez-office/)** · [Standalone source and automated tests](https://github.com/danieloculus0-bot/EZ-Office)

EZ-Office is a **working offline-first HTML/JavaScript office experiment**: Writer edits TXT/Markdown; Sheets imports/exports CSV; Slides presents text-based decks; Media opens browser-supported local audio/video/images; and Mail exports `.eml` drafts or hands off to a configured mail program. Five tools share one interface with on-demand loading and cleanup when switching. No login, cloud service, or separate application server is necessary for these functions.

The Workshop serves a pinned copy of the working application. It does **not** imply BEAN AI runs inside EZ-Office, that native DOCX/XLSX/PPTX documents are compatible, that mail accounts can synchronize, or that host-RAM savings were measured. Read the [EZ-Office README](https://github.com/danieloculus0-bot/EZ-Office/blob/main/README.md) for exact scope. EZ-Office is a separate project from BEAN Core and Axiom.

## New: BEAN-native reasoning and measured intuition (October 21, 2026)

- **[Workshop learning-results page](https://danieloculus0-bot.github.io/BEAN/portfolio/bean-learning/)**: mobile-friendly walkthrough of what was actually tested, with direct links to code, CI and evidence.
- **[Lab026 reasoning skills (draft PR #144)](https://github.com/danieloculus0-bot/BEAN/pull/144)**: source-linked experience recall, reflection on errors, reusable procedures, and controlled strategy selection using BEAN's existing SQLite Journal.
- **[Lab027 reinforcement-learning evaluation (draft PR #149)](https://github.com/danieloculus0-bot/BEAN/pull/149)**: real original SpongeTD Q-learning on 3,000 synthetic training puzzles, a separate 180-map tuning set, and **240 untouched holdout layouts**. Trained Q-learning with the same loop-avoidance controller solved 237/240 maps versus 232/240 for cold Q; mean moves were 21.7 versus 69.0. Exact Q-values survived checkpoint/restart.
- **[Verified Lab027 GitHub CI run](https://github.com/danieloculus0-bot/BEAN/actions/runs/39550106061)**: both Windows and Ubuntu succeeded on evaluated code revision `4d969b0e`, with inspectable compressed event-ledger artifacts.

These experiments demonstrate task-family learning and reusable mechanisms, **not** general intelligence, production deployment, external action authority or neural training. Both PRs remain experimental branches; they are not merged into `main`. The newest changes on a draft branch may be newer than the listed successful CI revision.

## Before any BEAN engineering work

**AI contributors: [Read and acknowledge the BEAN activity gatekeeper](docs/AI_GATEKEEPER.md)** (also referenced by [`AGENTS.md`](AGENTS.md)). Check connected BEAN memory where available, inventory existing branches/PRs and their CI, and read the compressed ledger before designing or modifying anything. This is a context-and-evidence gate, not a new runtime behavioral filter.

## Already-built learning infrastructure

- [**SpongeTD tabular Q-learning**](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-sponge-core-20261011/bean/optimization/sponge_td.py): real temporal-difference updates and scored, recoverable Q-value memory, with [holdout ledger](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-sponge-core-20261011/experiments/sponge_breakout/evidence/score_ledger.jsonl).
- [**SpongeDQN neural Q-network**](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-deep-q-learning-20261012/bean/optimization/sponge_dqn.py): experimental PyTorch 3→64→64→3 network with minibatch replay, target network, real gradient training and compressed neural checkpoint restoration. [Matched tabular/DQN/cold evaluation](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-deep-q-learning-20261012/experiments/sponge_breakout/deep_trial.py) is game-specific, not general neural recall or production runtime.
- [**Neural evolution**](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-deep-q-learning-20261012/experiments/sponge_breakout/evolve.py): candidate inheritance and mutation; trials include important regressions, not a replicated overall gain.
- [**Persistent compressed scoring ledger**](https://github.com/danieloculus0-bot/BEAN/tree/experiment/anticipatory-ledger-20261020/research/persistent_ledger): append-only historical evidence with small rebuildable scoring summaries.
- [**BEAN tests BEAN**](https://github.com/danieloculus0-bot/BEAN/pull/140): research-only indexed JUnit test retrieval, comparing verified options through the existing Core selector; neural retrieval training is *not* implemented.
- [**BEAN Bridge Lab009**](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/46): revised frozen-replay versus online-acquisition scoring (0/3 baseline, 2/3 after restart without new evidence, 3/3 after new synthetic research).
- [**BEAN-readable scoreboard and reward**](https://github.com/danieloculus0-bot/BEAN/pull/141): experimental JSON scoreboard context, signed reward for matched improvement/regression, and duplicate evaluation-credit detection. Not yet consumed automatically by the hosted BEAN connector or neural DQN.

These are **distinct research branches and draft PRs**, not all part of Core `main`. Consult [the public learning page](https://danieloculus0-bot.github.io/BEAN/#learning) and exact linked test receipts. All neural claims remain limited to controlled synthetic experiments.

## Current build state

**Reviewed:** 2026-10-20 · **Inspected main:** `4e4b5f84683f` · **Type:** working experimental/beta code; not automatically production-certified.

- [BEAN AIscend public demo checks](https://github.com/danieloculus0-bot/BEAN/actions/runs/39503225654) — **Passed** on an earlier `main` revision; the static demo has a separate check.
- [BEAN full core regression](https://github.com/danieloculus0-bot/BEAN/actions/runs/39512878059) — **Passed** at inspected `main` on Windows/Linux.
- [Pages build and deployment](https://github.com/danieloculus0-bot/BEAN/actions/runs/39512878048) — **Passed** at inspected `main`.

[See live Actions](https://github.com/danieloculus0-bot/BEAN/actions) for newer results; this is a dated evidence snapshot, not a continuously updated indicator.

## Implemented today

- Persistent memory, source/contradiction tracking and offline replay backed by runnable Core code.
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

Reproduce improvements on holdout tasks, verify restart continuity, and expand tested source integration without falsely claiming model learning or production autonomy.

## Documentation

- [BEAN site](https://danieloculus0-bot.github.io/BEAN/)
- [Research and verification docs](docs/experimental-research-index-2026-10.md)
- [**Complete prior README, including history and detailed instructions**](docs/archive/README_2026-10-20_before_refresh.md)

Historical experiments, dated reports and superseded architectural claims have been moved out of this landing page, **not deleted**.
