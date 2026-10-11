# BEAN Verified Utility and Experimental Evidence

**Snapshot date:** October 11, 2026. **Consolidation status:** Code and tests incorporated into BEAN Core `main` only after pull-request regression and an explicit merge.  
**Scope:** Reproducible developer and operator demonstrations. No proprietary ERP records, live financial returns, autonomous sentience, or robot deployment.

## 1. Run the four useful behaviors in one command

```bash
python -m pip install psutil
python -m examples.capability_proof
```

This runs **actual BEAN Core APIs**, not fabricated outputs or staged narration. It uses only temporary SQLite state and fictional observations.

| Proof | Executed underlying implementation | Observable pass condition | Crucial limitation |
| --- | --- | --- | --- |
| Durable continuity | `examples.restart_continuity.run_demo` → `BeanReasoningLayer` + SQLite | An event and pending-review proposal survive two distinct sessions | Reasoner is the mock fixture; temporary local DB |
| Conflicting reports | `bean.integration.public_plugin.compare_evidence` → real `EvidenceBridge` | Two incompatible submitted claims leave `conclusion=None`, with zero verified independent origins | Labels are user-submitted; no external source authentication |
| Claims and unauthorized actions | `audit_claim` + `screen_proposal` → real epistemic guard and proposal filters | Missing provenance is downgraded; motion-like proposed step gets no execution permission | Heuristics only, not safety certification |
| Missing data versus zero | `BeanWatcher` + `WatchSpec` + `ReportEvidence` | Missing report returns N/A and `None`; a complete host-attested report with `rma_count=0` returns verified zero | Fixture completeness/evidence are host-attested, not externally validated |

Machine-readable JSON reports `checks_passed`, `checks_total`, and the absence of network, model, business-data and hardware access. The CLI intentionally raises on an unmet condition. Its five regression tests run in the complete Core suite on Windows and Ubuntu, Python 3.10/3.12. Inspect [the Core CI workflow](../.github/workflows/brain-smoke.yml).

**Do not misinterpret this:** four green utility checks establish four bounded software behaviors, not independent real-world operational success. Model reasoning quality and financial profitability were not evaluated.

## 2. Useful modules that already live on Core main

| Existing module | Operator/developer utility | How to reproduce | Evidence |
| --- | --- | --- | --- |
| SQLite sessions and review proposals | An actual event, pending proposal and audit trail persist after restart | `python -m examples.restart_continuity` | [Restart tests](../bean/tests/test_restart_continuity_demo.py) and [Core CI](https://github.com/danieloculus0-bot/BEAN/actions/runs/38156840053) |
| Watcher and missing-data guard | Expired, incomplete, missing or stale quality exports do not silently become zero | `python -m pytest bean/tests/test_watcher.py -q` | [Watcher tests](../bean/tests/test_watcher.py) |
| Core↔Bridge evidence continuity | Two declared-source observations can establish a versioned *host-attested* finding; a contradiction reopens it across restarts | `python -m pytest bean/tests/test_evidence_bridge_contract.py -q` | [Core bridge tests](../bean/tests/test_evidence_bridge_contract.py) and [integration scope](EVIDENCE_BRIDGE_READINESS.md) |
| GitHub engineering journal | Track branches, PRs, changed CI outcomes and hash-chain evidence across local BEAN sessions | `python -m pytest bean/tests/test_github_engineering_bridge.py -q` | [Bridge tests](../bean/tests/test_github_engineering_bridge.py) and [operator guide](bean-github-engineering-bridge.md) |
| Cross-repo research inventory | Read-only, paginated audit of actual Core+Bridge branch ancestry, test modules, workflows and open reviews; emit JSON+Markdown | `python scripts/audit_research_inventory.py --output-dir audit-output` | [Offline tests](../bean/tests/test_research_inventory.py), [audit protocol](ENGINEERING_VALIDATION_2026-10-11.md), [original completed audit](https://github.com/danieloculus0-bot/BEAN/actions/runs/38123660781) |
| Read-only MCP evidence companion | Check unverified claims, conflicting submissions, review-only proposals and restart behavior using actual Core primitives | `python -m pytest bean/tests/test_public_plugin.py -q` | [Developer preview](../integrations/chatgpt/README.md); not a published ChatGPT Plugin |
| Code-review integrity primitives | Detect tampered original source, orphaned verdicts and rewritten message history | `python -m pytest bean/tests/test_peer_dialogue_lab017.py -q` | [Implementation](../bean/optimization/peer_dialogue.py) and [regressions](../bean/tests/test_peer_dialogue_lab017.py) |

A reproducible test does not authenticate user-provided source identifiers. BEAN does not have a hidden workforce of independent reviewers. The inventory does not infer feature completeness from Git commit ancestry.

## 3. Honest science: what the experimental scoreboard means

| Experiment | Observed result | Classification / code location | Actual receipt |
| --- | --- | --- | --- |
| Core regression at previous stable SHA | **559 passed, 1 skipped, 47 subtests passed, 84% coverage** on Ubuntu/Python 3.12; all four platform configurations passed | Real Core integration test result, not model quality | [GitHub Actions](https://github.com/danieloculus0-bot/BEAN/actions/runs/38156840053) |
| Aider vs BEAN neutral coding pilot | Both passed **16/16** withheld checks on two synthetic tasks | A **tie**, not a BEAN win | [Independent match](https://github.com/danieloculus0-bot/BEAN/actions/runs/38110050070) |
| BEAN selector source repair, Lab020 | Selected model-written repair passed **14/14** development and **7/7** separate final identity cases; comparator did not fix the original tested defect | Limited model-authored software repair in [Core research](BEAN_LLM_REPAIR_EXPERIMENT_20261011.md), not proof of generalized improvement | [Original research](https://github.com/danieloculus0-bot/BEAN/actions/runs/38109612791) |
| Qwen 1.5B clipping candidate | Source candidate passed **7/7** fixed independent tests on both Windows and Ubuntu | Tested but **unmerged standalone draft**. Not a broad coding skill claim | [Draft PR #74](https://github.com/danieloculus0-bot/BEAN/pull/74) |
| Lab005 evidence-sensitive search | **91.25% vs 18.75%** popularity baseline on deliberately syndicated synthetic sources | Synthetic ranking experiment in Bridge; not a live web search win | [Research CI](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38029876766) |
| Lab003 drifting-source detection | **78.57% vs 7.14%** recall in a *single* synthetic scenario; other scenarios regressed | Narrow research condition; do not turn into a universal score | [Research findings](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-evidence-intelligence-20261010/experiments/evolution_lab/LAB003_FINDINGS.md) |
| Five-specialist Lab025 | **5 INCONCLUSIVE** independent outcomes, against OpenCode, Goose, OpenHands, Continue and Cline | Infrastructure ran; zero confirmed victories | [Five independent verdicts](https://github.com/danieloculus0-bot/BEAN/actions/runs/38126634979) |
| Robot motion simulation | AVR/simavr and ESP32/QEMU pass, including a FreeRTOS task-delayed logical watchdog; native host passes 6,144 fault transitions and rejects a deliberately broken E-stop | [Bridge main experimental lab](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/experiments/robot_motion/README.md) merged via [PR #32](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/32). Wokwi `NOT_RUN_MISSING_TOKEN`; no actual hardware operation | [Fresh cross-emulator run](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38161744114) |
| OpenRouter free-model status | A single provider request returned **HTTP 429**, with **no generated candidate** | `NOT_TESTED`, despite green workflow bookkeeping | [Live attempt and independent validation](https://github.com/danieloculus0-bot/BEAN/actions/runs/38152611734) |

**Interpretation:** repeatable, independently challenged behavior enters stable Core only when the code is useful outside its lab and survives CI. Every historical result remains linked even when the related code is excluded from main. One small benchmark or provider error must not be described as BEAN defeating an agent.

## 4. Bridge and host integrations: useful, but distinct

- [Bridge Daily Exception Brief](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/docs/DAILY_EXCEPTION_BRIEF.md): **on Bridge main**, produces local HTML+JSON quality exceptions from an existing authorized export ledger. No live JobBOSS credentials or company data included. Missing OTD/RMA coverage is surfaced rather than invented.
- [Core↔Bridge evidence tests](EVIDENCE_BRIDGE_READINESS.md): the reusable `EvidenceBridge` lives on **Core main**. Its claims require trustworthy host verification, and identifiers alone are not independent proof.
- [AIscend](https://github.com/danieloculus0-bot/AIscend): separate project using BEAN-style components and independent Strategy School research. BEAN Core does not execute AIscend trading policies or manage wallets.
- Robot/CAD, embedded MCU experiments, local-model self-improvement branches and OS experiments: **opt-in research**. A green emulator is not physical control; a branch is not a production release.

## 5. Promotion and usefulness gate

For each future experiment: name a concrete user task; capture an immutable source SHA and a reproducible command; preserve failures, counterexamples and no-data states; test against independently checked fixtures; establish real host permissions; keep live actions separate from model suggestions; record CI URLs; merge only the minimal verified change, not an entire stale branch. Useful code must appear in the Core public API or documented CLI, not solely an experiment's README.

**Still unproven:** live ERP integration, authenticated open-world evidence, stable multi-tenant services, autonomous deployment of code without review, independent sustained operator time savings, real-money trading returns, general intelligent agency, and physical robot performance.

Latest utility audit: [BEAN usefulness audit](BEAN_USEFULNESS_AUDIT_2026-10-11.md). Source of truth for the latest test status is GitHub Actions, not a static test count copied into documentation.
