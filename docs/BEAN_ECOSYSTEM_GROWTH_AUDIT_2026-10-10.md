# BEAN ecosystem growth audit — October 10, 2026

Snapshot scope: BEAN Core and BEAN-AI-Bridge-, owned by danieloculus0-bot. The original inventory found **35 Core branches and 19 Bridge branches** (54 total) and no remaining branch-pagination results. The linked account has 13 repositories; the two named BEAN repositories were fully enumerated. New promotion branches created during the audit are not part of that initial 54 count.

## Verified production-source promotions

| Capability | PR | Acceptance boundary |
| --- | --- | --- |
| Hardened Watcher replay and fail-closed smoke tests | [Core #17](https://github.com/danieloculus0-bot/BEAN/pull/17) | Already in main before audit |
| Opt-in durable task engine | [Core #23](https://github.com/danieloculus0-bot/BEAN/pull/23) | Green four-platform CI; strict allowlist, at-most-once crash handling, disabled without trusted config |
| Offline JobBOSS spreadsheet import and management evidence reporting | [Bridge #10](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/10) | Green dedicated and generic Linux/Windows CI; no live ERP connection |
| Versioned definition and deterministic model-output gate | [Bridge #11](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/11) | Green Linux/Windows regression; validates library membership and citation shape, not independent source truth |
| Offline seven-stage capability examiner | [Core #24](https://github.com/danieloculus0-bot/BEAN/pull/24) | Green four-platform CI; mock baseline deliberately fails capability exam |
| SQLite memory database reinit isolation | [Core #25](https://github.com/danieloculus0-bot/BEAN/pull/25) | Standalone two-database regression; see PR for current merge/CI status |

Promoted code does not imply an operational unattended service, deployed ERP integration, autonomous self-modification or an LLM that learns by itself.

## Growth tracks compared with main

**Core main** already contains memory, identity, uncertainty, epistemic controls, supervised optimization proposals, bounded reasoning interfaces, Watcher and host/runtime infrastructure. The newly staged Core chain runs from **Lab011 durable tasks** through **Lab012 exam, Lab013 source-calibration growth, Lab014 investigation/retention, Lab015 symbolic reasoning emulation and Lab016 hosted-model probe**. Labs 013–016 are stacked experimental branches, not independent fully mature modules.

**Bridge main** owns deterministic ERP observation replay, source ledgers and reporting. Branches explored **Labs 001–007 evidence/intelligence/source reliability/confidence ranking**, **Lab008 definition verification**, two different **Lab009 native gateway / evidence-learning loop** prototypes, **Labs012–014 broad self-improvement and recovery**, JobBOSS spreadsheets, robot-body simulations and other sealed research trials. Overlapping lab numbers must be qualified by repository.

## Independently checked negative findings

- [Core hosted Lab016](https://github.com/danieloculus0-bot/BEAN/actions/runs/38101183581) successfully recorded its provider as UNAVAILABLE after one non-JSON service response. The hosted real-model paired comparison did **not** execute. Successful CI is not evidence of a successful LLM investigation.
- [Bridge Lab014](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/9) tested 1,520 new synthetic worlds and counted 66 policy switches, including 36 returns to earlier strategies. It lost approximately **104 reward units** versus equal-audit Lab013, with five stage regressions beyond its preregistered limit. Broad self-correction **was not demonstrated**.
- Core Lab013 verified a SQLite reinitialization bug: a new MemoryStore could retain the old thread-local connection; the narrow repair is in Core #25.
- [Bridge Lab008](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/2) showed real local Qwen2.5 model-output contract sensitivity; the stronger model's high acceptance rate does not prove factual reliability, so only the deterministic gate was promoted.
- The [native inference gateway](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/3) implements bounded symbolic lookup, **not** a general-purpose replacement for Ollama or a neural model.

## All original branches inspected for presence and main-diff status

### Core — 35 including main

main; audit/harden-watcher-and-smoke-20261010; bean-core-virtue-001; brain-0.13-code; brain-0.13-commit; brain-0.13-commit-real; brain-0.13-commit-test; brain-0.13-final; brain-0.13-final-write; brain-0.13-final-write-actual; brain-0.13-normalized; brain-0.13-normalized-work; brain-0.13-speculation-reasoning; brain-0.13-speculation-reasoning-2; chatgpt-bean-os-installer; chatgpt-brain-0.13-recovery; chatgpt-windows-installer; docs/bean-research-findings-20261010; experiment/bean-capability-lab-20261009; experiment/bean-composite-growth-lab013-20261010; experiment/bean-entrance-exam-lab012-20261010; experiment/bean-github-hosted-llm-lab016-20261010; experiment/bean-investigation-retention-lab014-20261010; experiment/bean-simulated-llm-lab015-20261010; experiment/bean-task-autonomy-lab011-20261010; experiment/trust-evidence-filter-lab010-20261010; feat/native-bean-watcher-recall-20261010; feature/bean-memory-core-0-1; feature/body-motion-complete; feature/body-motion-teaching-core-0-1; feature/general-reasoning-layer; feature/pet-the-bean-virtual-affection-20261010; fix/bean-core-stabilization-20261010; fix/bean-origin-context-20261010; fix/bean-watcher-smoke-entry-20261010.

Most historical brain-0.13 variants are entirely behind main; legacy installer/recovery branches diverge and contain overlapping older reasoning code. Do not wholesale merge or delete based solely on ahead/behind counts.

### Bridge — 19 including main

main; audit/validate-smoke-phase-20261010; experiment/bean-broad-improvement-lab012-20261010; experiment/bean-confidence-search-lab005-20261010; experiment/bean-dynamic-output-gate-lab008-20261010; experiment/bean-epistemic-continuity-lab006-20261010; experiment/bean-evidence-intelligence-20261010; experiment/bean-evolution-lab-20261009; experiment/bean-learning-loop-lab009-20261010; experiment/bean-model-revision-lab004-20261010; experiment/bean-native-inference-lab009-20261010; experiment/bean-ollama-verifier-lab007-20261010; experiment/bean-recovery-guard-lab014-20261010; experiment/bean-robot-body-lab001-20261010; experiment/mcdonalds-evidence-001-20261010; experiment/remote-viewing-blind-vault; feat/puppy-adjacent-smoke-phase-20261010; feat/venvwin-smoke-lab-20261010; feature/jobboss-spreadsheet-sponge-20261010.

Bridge's experiment branches share several inherited modules and workflows, so branch commit totals cannot be added together to estimate unique learning.

## Remaining engineering gaps

1. The generic Bridge KPI calculator still emits some literal zeros when there is no complete source-coverage manifest; unavailable must be distinguished from verified zero before authoritative reporting.
2. Generic Bridge batch ingestion commits individual events, allowing partial writes before a late conflict. Atomicity and rollback regression are desirable.
3. Model-produced citations need upstream evidence authenticity, source independence and drift calibration, not merely syntactic validation.
4. The Core hosted-model Lab016 requires a real completed paired inference study before any real-model learning claims.
5. Unnecessary policy switching and recovery after changing source reliability remain open, as evidenced by Lab014 failure.
6. BEAN has no independently verified live ERP adapter, venvWin boot test, unattended production-host monitoring or hardware servo learning from this repository scan.

**Promotion rule:** integrate narrow, tested capabilities and their receipts; keep failed evidence; compare against current main; require new full cross-platform CI. Preserve experimental branches until their work and evidence are independently consolidated. No automatic cleanup or branch deletion is authorized by this audit.
