# Get started with BEAN

BEAN (Behavior Enabled Avatar Node) is a **public-source persistent reasoning and evidence architecture**. Its Python core can record observations, store traceable proposals, and call replaceable reasoning providers. This is an experimental developer project, not a turnkey agent or a claim of AGI.

## An offline example in about five minutes

Requirements: Python 3.10+ and Git. The demo uses a **temporary local SQLite database** and BEAN's **mock provider**. It makes no external requests and does not control hardware or an ERP.

```bash
git clone https://github.com/danieloculus0-bot/BEAN.git
cd BEAN
python -m pip install psutil
python -m examples.quickstart_reasoning
```

The example records a fictional observation and returns trace identifiers for a stored, review-required proposal. Its output includes `event_id`, `proposal_id`, `requires_supervisor_review`, `motion_command_generated` and `memory_written`. Identifiers vary per run. **The mock provider is a fixture, not a capable trained language model.** This demo shows the plumbing and review boundary, not BEAN's comparative intelligence or restart persistence. The temporary database is deleted after the demonstration.

## Validate the existing implementation

```bash
python -m pip install pytest pytest-cov psutil
python -m pytest bean/tests/test_general_reasoning_layer.py -q
python -m bean.runtime.boot_readiness --temp
```

For the full regression suite:

```bash
python -m pytest bean/tests -q
```

The repository's [cross-platform workflow](https://github.com/danieloculus0-bot/BEAN/actions/workflows/brain-smoke.yml) exercises Linux and Windows on Python 3.10 and 3.12. A passing suite verifies tests and specified contracts, not intelligence outside those tests.

## Explore something more substantial

- [Core architecture](../README.md) and [host-neutral reasoning API](general-reasoning-layer.md).
- [BEAN Watcher](bean-watcher-contract.md): local, opt-in report inspection; absent coverage returns N/A instead of invented zeros.
- [Evidence continuity across Core and Bridge](EVIDENCE_BRIDGE_READINESS.md): typed host-attested source evidence and uncertainty review.
- [Reproducible research experiments](experimental-research-index-2026-10.md): source branches, CI results, negative findings and limitations.
- [BEAN AI Bridge](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-): separate generic ERP/KPI evidence ledger, synthetic fixtures and replay. Not a deployed production integration.

## Current boundaries

Real source authentication, production ERP ingestion, general hosted-model evaluation, robust deployment, independently validated learning gains and robot autonomy remain open work. A proposal is **never authorization to execute**. Host systems own their permissions and effects.

Public GitHub visibility alone does **not** imply a redistribution license. Check the repository's licensing status before redistributing or incorporating code in another product.

Questions and reproductions: [open an issue](https://github.com/danieloculus0-bot/BEAN/issues). Include OS, Python version, exact command, observed result and non-sensitive traces.
