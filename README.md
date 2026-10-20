# BEAN 🌱

Persistent experimental reasoning and evidence system. BEAN Core maintains SQLite-backed observations, source-aware claims, revision history, recovery and repeatable research tests. It is not a production-grade autonomous software engineer.

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
