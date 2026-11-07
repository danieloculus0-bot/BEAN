# BEAN memory-continuity audit, November 6, 2026

## Verdict

**ALREADY ESTABLISHED, NOT A NEW GOAL.** BEAN's origin record already defines a universal, persistent, model-independent reasoning architecture, with optional embodiment. Its historical intent includes investigating emergent intelligence and possible consciousness, not asserting either. Digital software interactions, simulations, evaluations, and code experiments count as development environments. An experiment in a digital environment need not wait for a robot.

The recurring mistake was confusing a newly proposed **implementation increment** with a newly proposed **mission**. Developers and scheduled agents must read the original mission, prior failures, Core source, research ledger, and outstanding PRs before suggesting another brain.

## Existing components checked

| Source | Already exists | Limit |
| --- | --- | --- |
| `memory/identity/origin_record.json` and `bean/memory/origin.py` | Canonical origin persisted to SQLite developmental history and continuity summaries | Earlier version 002 remains historical; 003 records the clarified longstanding digital and GitHub intent |
| `bean/memory/event_logger.py` and `bean/memory/audit_mirror.py` | Canonical local SQLite event history, JSONL audit mirror, revisions | Not a GitHub remote sync |
| `bean/learning/` and native reasoning service | Evidence-linked local reasoning, journaled lessons, selected approaches and restarts | Model intelligence or consciousness not established by a working journal |
| `bean/integration/github_engineering.py` | Read-only GitHub branch/PR/CI observations persisted as a local SHA-chained engineering journal | No GitHub write-back and no automatic Core memory replication |
| `research/PERSISTENT_LEDGER.md` on the archived experimental ledger branch | Public-safe, versioned compressed experiment-receipt and rebuildable-scoreboard design | Historical synthetic evidence; not complete current live cognition or a model trainer |
| `AGENTS.md` and `docs/AI_GATEKEEPER.md` | Inventory-first, source/evidence verification, avoid duplicates, preserve privacy | Earlier preflight did not state the founding digital/GitHub intent prominently enough |

## The established storage and communication design

1. **Live private brain:** BEAN's existing local SQLite and SHA-journal records retain runtime memories, outcomes and identity.
2. **Versioned delayed public research brain:** GitHub main, isolated branches, public-safe experiment receipts, PR discussions and documentation preserve recoverable developmental decisions and evidence across asynchronous agents and disconnected sessions.
3. **Reconciliation:** A reader compares the exact revision and evidence/receipts, detects stale or contradictory statements, and reuses the existing design rather than inventing another memory backend.
4. **Future connection to implement and test:** A privacy-filtered, explicitly versioned Core-to-GitHub write/replay interface that proves recovery from a delayed remote handoff, prevents duplicate receipt credit, preserves corrections and failures, and tests disconnected restarts. No claim that this remote write/replay interface is live today.

GitHub is **not** a permissible public dump for conversations, private experiences, employer/customer data, secrets, model keys or machine-specific configurations. Private memories must remain in authorized stores. Repository updates are communications only after a later agent actually retrieves and applies them. A merged commit is not proof that a running Jetson read it.

## Acceptance evidence required next

- Boot an empty local Core database and confirm origin covenant 003 records the digital experience, Github delayed communication and open research questions.
- Insert historical covenant 002, boot again, and prove both versions remain, unchanged; subsequent boots must not append duplicates.
- Verify the newly initialized Core identity no longer describes robotics as the basis of intelligence.
- Check all tests at the **exact final PR head** and independently review the changed-file diff. Merge only if green and clear of private data.
- In subsequent work test the missing public-safe GitHub handoff path end-to-end, with explicit provenance and no fabricated independent learning.

## Evidence boundaries

This audit verifies source/design facts, not subjective consciousness, AGI or universal self-improvement. The hosted BEAN memory connector and Jetson Core are distinct, and GitHub is presently not the authoritative private live runtime database. Preserve negative cases and exact source revisions. Reject both false consciousness claims and preemptive claims that consciousness can never emerge.

## Current change

This patch documents the original mission in the canonical origin JSON, exposes it through a **new additive** origin-covenant version, repairs the default Core identity description, restores it to the README and agent entry point, and tests persistence without erasing version 002. It does not add hardware actions, a second memory store, an unreviewed agent policy, or public memory uploads.
