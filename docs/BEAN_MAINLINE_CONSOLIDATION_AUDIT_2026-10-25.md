# BEAN Core — Mainline consolidation and code audit
Date: 2026-10-25. Evidence: BEAN GitHub main, PR history, actual source and experiment archives.

## Engineering policy

Promising working capabilities belong on **main**, labeled experimental where appropriate. Experimental evidence and user-computer proof are different from repository integration. Fix broken implementations *on main*; keep the raw failed experiments in their original Git histories. A conflict with current architecture calls for reconciliation, not blanket rejection as "unverified."

## Consolidated into Core

| PR | Actual mainline work |
| --- | --- |
| [#170](https://github.com/danieloculus0-bot/BEAN/pull/170) | NativeReasoningService: generated rules, source-linked error reflections, durable SQLite learning ledger, paired outcome strategy selection, future lesson retrieval, replaceable real model inference, default-on Python inbox |
| [#171](https://github.com/danieloculus0-bot/BEAN/pull/171) | Real Nemotron research runners, tests and original evidence references copied into mainline Python research |
| [#172](https://github.com/danieloculus0-bot/BEAN/pull/172) | Previously stranded Core curiosity/goal generation and reasoning-prompt context connected |
| [#174](https://github.com/danieloculus0-bot/BEAN/pull/174) | Read-only conformity audit from #100 plus Bridge verifier; bounded atomic Core inbox and private-content-safe event logging |
| [#175](https://github.com/danieloculus0-bot/BEAN/pull/175) | Structured memory/numeric cognition/experiment/drive blocks from old #131/#132; cognitive reasoning delegated to the existing native service |
| [#176](https://github.com/danieloculus0-bot/BEAN/pull/176) | Real inference feedback: host-observed correct and incorrect outcomes, evidence-linked corrections, idempotent receipt handling, failed-provider journal entries, cleaner error logging |
| Current patch | Unique repeated-inference receipt IDs; one rather than two complete journal reads before appending; historical compressed Nemotron recovery source and failure receipts brought to main |

## Specific code audit findings

1. **Request handling fixed:** `bean/runtime/inbox.py` could see partially written JSON, queue overlarge input and log raw prompts and results. It now uses atomic .tmp writes, 64 KiB intake limits, quarantine on invalid JSON, and metadata-only event logs. A second pass removed raw parse/command error echoes. Handler results remain returned to their authorized caller.
2. **Missing learning handoff fixed:** `bean/learning/reasoning_service.py` can now connect a specific model answer to its positive or negative host-observed outcome via `reasoning_feedback`; it stores both outcomes and source-linked correction hypotheses in BEAN's one SHA journal. Host ratings are **not** automatically authenticated.
3. **Outages previously invisible:** attempted provider failures are now retained as failed inference receipts, including exception type but not secret/error body. No fake answer is awarded for a missing configuration.
4. **Duplicate inference identity fixed:** repeated identical prompt/context/answer combinations originally hashed to identical receipt IDs, breaking unique feedback linkage. A new journal sequence field prevents collision; earlier hashes remain valid.
5. **Wasteful full-ledger scan optimized:** `ExperienceBank._append` previously read/verified the entire history just to compute the next iteration, then `Journal.append` performed its own verification. A constant-time count replaces the redundant pre-scan; the SHA-chain validation remains mandatory on append.
6. **Multiple reasoning paths:** historical `ReasoningEngine` and Bridge blocks remain for compatibility. New `cognition_reason` flows to the one `NativeReasoningService`, not another copy of a reasoning brain.
7. **Remaining scale debt:** SHA validation on every append and lexical memory scans are still O(history); over many writes, runtime can grow superlinearly. Indexed retrieval and incremental verified checkpoints should be built with tamper-preserving tests.
8. **Inference rate/cost policy:** OpenRouter HTTP 429 stopped multiple actual Nemotron study runs. Per-arm batching and an archived recovery script are available; work remains to budget/resume multi-provider inference without blind retry loops.
9. **Cross-app ownership:** BEAN Bridge, AIscend, Axiom and hosted BEAN notes are not automatically synchronized with Python Core. They need authenticated adapters to Core's existing evidence/reward APIs, not second memory stores.

## Stale research branch disposition

- **#144/#167/#168/#169:** useful native reasoning and Nemotron functionality is now in main via #170/#171/this patch. The original experiment SHA hashes, responses and failed runs remain in their historical branches. Close stale PRs as superseded while retaining source history.
- **#100:** read-only source-audit and Bridge verification functionality integrated in #174, without exposing the old research workflow as a production action.
- **#131/#132:** Core cognition and Bridge-compatible block methods integrated through #172/#175; older branch tests retain their historical meaning.
- **#8:** Brain 0.9–0.13 recovery contains obsolete replacements of newer Core reasoning/speculation modules. Merging its entire old tree would regress current interfaces; evaluate only genuinely unique functions against current Core.
- **#115:** optional local MCP note interface currently represents a second limited lexical-memory path. The worthwhile integration is an *authenticated connector to the existing BEAN-owned service*, not permanently maintaining a competing memory owner. The proposal is not discarded; auth/routing reconciliation remains.

## Design rule

**BEAN generates, remembers, compares and selects reasoning strategies.** It owns feedback and state. Nemotron, OpenAI and future engines supply replaceable inference, while tabular/DQN training remains a separate optimization mechanism until explicitly connected to the same observed outcomes. The runtime must be extendable without a permanent island of unmerged useful code.

This audit does **not** claim autonomous general intelligence or profitable trading. Source integration, reproducible tests, source trust and measured adaptive performance are recorded separately rather than used as excuses to bury progress.
