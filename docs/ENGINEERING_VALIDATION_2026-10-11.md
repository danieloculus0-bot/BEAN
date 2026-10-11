# BEAN Engineering Validation and Research Consolidation
**Kickoff:** 2026-10-11  
**Core baseline:** main at fa68d70a8108e4342dcb5972fb933d20ec3c370c  
**Working branch:** audit/bean-engineering-validation-20261011  
**Disposition:** research review, not permission to merge, act on a host or claim production readiness.

## Scope and baseline evidence

Audit BOTH [BEAN Core](https://github.com/danieloculus0-bot/BEAN) and [BEAN AI Bridge](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-).

- Core: **89 pre-audit branches** (plus this newly created audit branch), **70 main test modules**, **17 main workflow files**, **7 open pull requests**.
- Bridge: **42 branches**, **12 main test modules**, **11 main workflow files**, **9 open pull requests**.
- Root ARCHITECTURE.md still depicts Memory Core 0.1; the README describes many later modules. Historical design, main code, opt-in components, experimental implementations, CI-tested contracts and real deployment outcomes need separate labels.
- [Main Core four-configuration regression succeeded](https://github.com/danieloculus0-bot/BEAN/actions/runs/38122197868) on baseline SHA. A separate [BEAN vs Aider workflow failed](https://github.com/danieloculus0-bot/BEAN/actions/runs/38121744685) on an earlier SHA. A green core suite does not imply all experiments are passing.
- [Research consolidation issue #52](https://github.com/danieloculus0-bot/BEAN/issues/52) records prior promotions and warns that Git ancestry can misrepresent squash-merged capabilities. Its older branch counts need refreshing.

### Reproduce the branch and test inventory

From this audit branch, execute:

    python scripts/audit_research_inventory.py --output-dir audit-output

The **read-only** tool paginates both repositories' branches and open PRs, records their main SHA and complete main test/workflow file lists, and compares **every non-main branch** against its current main. It produces audit-output/inventory.json and audit-output/inventory.md. It records partial errors rather than silently declaring success. Set GH_TOKEN or GITHUB_TOKEN in the environment if authentication is needed. The audit GitHub Actions job checks its offline unit tests and retains both results as evidence.

**Caveats:** ahead/behind is commit ancestry, not semantic uniqueness; squash-merged work may still appear ahead or diverged. API comparisons may cap file lists. Green tests demonstrate tested contracts, not AGI or independent truth. API errors make an audit incomplete. Archive evidence links; temporary CI artifacts expire.

## Engineering findings and ordered gates

| Priority | Concern and supporting source | Required independent acceptance |
| --- | --- | --- |
| P1 | **Event/evidence durability:** bean/memory/event_logger.py commits SQLite and subsequently appends a package-relative JSONL record. The authoritative DB can succeed while JSONL fails. Existing bean/tests/test_memory_core.py checks normal event writes. | Simulate crashes, interrupted writes, read-only package locations and multi-process output; implement UUID-based, idempotent DB-to-JSONL reconciliation and verified restart behavior. Do not silently discard errors or history. |
| P1 | **Capability truth:** ARCHITECTURE.md, README.md and docs/experimental-research-index-2026-10.md differ in scope and date. | Publish an exact stable/opt-in/research/deployed capability matrix with implementation paths, tests, limitations, CI refs and unknowns. |
| P1 | **Independent reasoning baselines:** the architecture's persistence, uncertainty and evidence-trust machinery has not yet shown superiority to well-matched LLM retrieval baselines on independently unseen tasks. | Preregister cases, budgets, seeds, context, prompts, information access, metrics and holdouts; compare conventional LLM, LLM+retrieval, BEAN-no-persistence, BEAN individual trust/uncertainty ablations, full BEAN. Include conflicts, drift, correlated sources and legitimate abstention. |
| P2 | **Peer integrity:** bean/optimization/peer_dialogue.py, code_candidate.py and draft [PR #33](https://github.com/danieloculus0-bot/BEAN/pull/33) offer digest-pinned proposals, not reviewer identity authentication or approved auto-execution. | Challenge reordered messages, replaced originals, forged evidence IDs, stale/replayed CI and false reviewer identity. Verify repo, SHA, CI job and provenance independently. |
| P2 | **Host boundary:** bean/integration/github_engineering.py is a read-only observer; its builder/reviewer/tester names are suggested roles, not independently running agents. External evidence IDs are host-attested. | Authenticate evidence origins; reject unauthorized operations and spoofed host reports; require explicit effect authorization and independent reviewers before GitHub writes, workflow dispatch or production actions. |
| P2 | **Promotion collision:** many research branches diverge from current main and overlap with squash-promoted files. See [issue #52](https://github.com/danieloculus0-bot/BEAN/issues/52). | Diff exact HEAD trees against main; preserve negative outcomes, isolate minimal changes, validate hidden holdouts and avoid entire-branch merges. |
| P3 | **Measurable application:** Bridge has a read-only daily manufacturing exception brief but no independent ten-workday time/value assessment (docs/BEAN_USEFULNESS_AUDIT_2026-10-11.md). | Shadow report with approved offline exports, independent KPI definitions, N/A correctness, measured time saved and zero unsupported claims. Never commit confidential exports. |

## Experiment families and specific review questions

### Core 0.1–0.14 and main regressions
- Memory/schema/session/restart, identity/world state and runtime: add fault injection, corruption recovery and cross-instance tests.
- Epistemic guard, falsification, contradiction court, uncertainty, relationship trust and reasoning context: test malicious provenance and mutually contradictory modules.
- Voice, Ollama/reasoning adapters, motion and robot: distinguish mock tests from live model calls, simulated motion and actual hardware validations.

### Core labs 010–025
- **010:** trust/evidence/care context from open [PR #13](https://github.com/danieloculus0-bot/BEAN/pull/13); privacy and source authenticity must be independent.
- **011–015:** durable tasks, entrance examination, composite growth, investigation retention and simulated LLM; reproduce cold starts, holdouts and losing conditions before promoting heuristics.
- **016–019:** hosted reasoning, cross-branch peer dialogue, synthetic triad falsification and autodraft; roles that emit scripted test records are not live independent agents.
- **020–025:** model-written repair, autonomy transfer, self-repair, causal retention and Aider/specialist duels; verify actual model invocation, source digests, valid candidate rate, feedback leakage, cost, paired holdouts and failures. Important open drafts include [PR #51](https://github.com/danieloculus0-bot/BEAN/pull/51) and [PR #74](https://github.com/danieloculus0-bot/BEAN/pull/74).
- **Robot CAD and historical investigations:** evaluate under domain-specific scientific criteria. They do not count as general intelligence by default.

### Bridge labs and integrations
- **001–006:** evolution/source reliability/model revision/confidence search/epistemic continuity. Retain observed regressions, verification expenses and correlated-source failures; most evidence is synthetic.
- **007–009:** verification, definition gates and experimental inference proxy; require live-provider traceability, invalid responses, timeouts and an explicit deployment boundary.
- **012–014:** broad improvement/recovery/independent peer challenges; preserve negative holdouts and host-control checks.
- **JobBOSS/ERP reporting, manufacturing exceptions, robotics/OS, and other scoped studies:** isolate from stable reasoning claims until host contracts and independent deployments are validated.

The inventory artifact enumerates *every actual branch and test filename* and highlights overlapping/aged branch revisions for reviewer classification. Existence of a test file is not proof of its recent passing status.

## Engineering-team assignment protocol

This is an **invitation to explicit work**, not a claim that BEAN already has autonomous reviewer agents listening for issues:

1. **Builder:** reproduce a defect then propose the smallest code diff pinned to the current base SHA; provide rollback and a proposed acceptance test.
2. **Falsifier:** independently generate negative tests without revealing hidden answers to Builder, including SQLite/JSONL fault injection, fake evidence and forged review status.
3. **Tester:** run exact pinned commits and relevant suites on Windows/Linux; return test counts, commands, CI jobs, failed cases and observed resource usage.
4. **Reviewer:** verify identities and receipts, assess the competing baseline, identify duplicate or already-promoted source and record unresolved objections.
5. **Maintainer/owner:** approve or reject any merge after independent results; human or authorized gate remains in charge.

**Mandatory promotion gate:** reproducible source SHA and data, clean holdout separation, explicit unknowns, independently challenged evidence, safety/authorization testing, fair baselines and measured benefit, reversible opt-in integration, successful required CI and explicit approval.

Comments, PRs and CI artifacts are a shared *asynchronous evidence surface*, not a secret live channel connecting ChatGPT sessions. Do not invent reviewer identities or claim an agent has taken an assignment. Maintain the existing stable main branch while this audit runs.
