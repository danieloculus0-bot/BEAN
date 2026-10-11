# Contributing to BEAN 🌱

BEAN is an experimental Python project for evidence-aware persistent reasoning. The most valuable contributions are **reproducible results, falsifications, careful bug reports, documented integrations, and code with tests**. A GitHub star is welcome if the project is useful, but a measured independent result is more useful than empty praise.

## Reproduce the baseline

Requires Python 3.10+, Git, and local ability to install `psutil`.

```bash
git clone https://github.com/danieloculus0-bot/BEAN.git
cd BEAN
python -m pip install psutil
python -m examples.quickstart_reasoning
```

This uses a **mock** reasoning provider and a disposable database. It is not evidence of live autonomous model learning. See [the full guide](docs/GETTING_STARTED.md) for platform-specific notes.

## What to test

- The separation between **model proposals** and authorized effects.
- SQLite persistence and restart recovery.
- Missing, stale, conflicting or spoofed evidence and clear **unknown/N/A** states.
- Duplicate source origins and whether unsupported conclusions remain unresolved.
- Evidence references surviving replays without rewriting history.
- Documentation errors, overly strong public claims, and confusing install steps.
- Cross-platform differences between Windows and Linux.

Existing experimental outcomes, including negative ones, are indexed in [research evidence](docs/experimental-research-index-2026-10.md). The [BEAN AI Bridge](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-) is a separate project; open an issue there for Bridge-specific problems.

## Report back

Open an [issue](https://github.com/danieloculus0-bot/BEAN/issues/new/choose) with:

1. Exact BEAN commit SHA, OS and Python version.
2. The command used, the expected behavior and what actually happened.
3. A **minimal synthetic** reproduction and relevant traces or test output.
4. Whether the outcome reproduced after restarting with a fresh temporary database.
5. Any suspected security, data leakage, or unintended action boundary.

Do **not** post API keys, proprietary ERP exports, personally identifiable information or customer files in public issues.

## Proposed changes

Start with an issue for larger features, work on your own branch, keep patches small, add regression tests, and provide a clear before/after comparison. Explain **how** evidence was authenticated and which assumptions remained unchecked. Do not claim a positive result from green CI alone when a workflow is designed to discover and report problems.

`main` should contain tested reusable capabilities; unfinished experiments should remain clearly identified. New features should preserve review boundaries and avoid granting effectors, tools or external network access by default.

## Reuse terms

The project is publicly readable on GitHub, but the repository owner has not chosen a software redistribution license yet. **Public visibility is not permission to reuse or redistribute code.** Contributions do not implicitly change the licensing status. Please contact the maintainer via an issue before relying on the code in another distributed product.

Thanks for helping this little bean grow carefully.
