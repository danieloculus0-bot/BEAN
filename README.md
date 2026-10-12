# BEAN 🌱

<p align="center"><img src="docs/bean-official.webp" alt="BEAN official mascot: smiling lime-green bean waving with a two-leaf sprout" width="180"></p>

**Behavior Enabled Avatar Node** · Public-source experimental AI technical beta (redistribution license not yet specified)

**BEAN has usable skills today.** Persistent SQLite memory and recovery, evidence-first reasoning and revision, offline quality briefings, scheduled tasks, engineering audit reports, local Ollama/Windows voice and read-only MCP tools all have runnable code. The Bridge also has independently tested Arduino Nano/ESP32 emulator logic. AIscend is a runnable Coinbase crypto-trading beta using BEAN-style research, market memory and buy-confirmation checks. Those are real capabilities even without enterprise hosting. [**Explore the skill showcase**](https://danieloculus0-bot.github.io/BEAN/#capabilities) or [**inspect the evidence ledger**](docs/VERIFIED_UTILITY_AND_EVIDENCE_2026-10-11.md). Specific local setup and source authentication requirements still apply; a technical beta isn't an unattended hardware or trading release.

[**Live site**](https://danieloculus0-bot.github.io/BEAN/) · [**Learning lab**](https://danieloculus0-bot.github.io/BEAN/#learning) · [**AIscend demo**](https://danieloculus0-bot.github.io/BEAN/aiscend.html) · [**Production-readiness audit**](docs/PRODUCTION_READINESS_AUDIT_2026-10-11.md) · [**Verified utility and evidence**](docs/VERIFIED_UTILITY_AND_EVIDENCE_2026-10-11.md) · [**Five-minute quickstart**](docs/GETTING_STARTED.md) · [**Tested Windows desktop beta**](docs/WINDOWS_DESKTOP_BETA.md) · [**Verified memory backups and release gate**](docs/BEAN_BACKUP_RELEASE_GATE_2026-10-12.md) · [**Research index**](docs/experimental-research-index-2026-10.md) · [**Contribute**](CONTRIBUTING.md)

[![Core regression: Windows and Ubuntu](https://github.com/danieloculus0-bot/BEAN/actions/workflows/brain-smoke.yml/badge.svg)](https://github.com/danieloculus0-bot/BEAN/actions/workflows/brain-smoke.yml)

> **Cute name. Serious reasoning. Real receipts.**
>
> BEAN is the persistent layer for systems that need to remember, question, track evidence, preserve uncertainty, recognize contradictions, propose improvements and keep an auditable record of what really happened. It can use an LLM, a desktop, a service, a manufacturer's data exports or a robot as a host. **None of those is BEAN's identity. The body is optional.**

## Why BEAN is more than an LLM call

The distinction is not that BEAN invented memory or tool use. Those are standard agent techniques. BEAN's contribution is an inspectable **evidence-to-action loop**: source-aware records survive restarts, contradictions remain unresolved until evidence supports revision, model proposals stay distinct from permission to execute, and engineering candidates can be judged against repeatable tests. **Its intelligence advantage is a research question, not an asserted fact.**

There are concrete outcomes beyond a feature list:

- **Merged, bounded Bridge source changes:** BEAN selected from known, evidence-backed improvements, and a trusted executor applied regression-tested changes: [invalid-observation validation, PR #15](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/15) and [timestamp-parsing optimization, PR #17](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/17). Both merged. These are constrained agentic changes, not freeform neural self-rewriting.
- **External model-authored Core repair:** [Lab 020](docs/BEAN_LLM_REPAIR_EXPERIMENT_20261011.md) reports 14/14 development plus 7/7 independent holdout checks for a proposal to repair BEAN Core's selector. [Review PR #51](https://github.com/danieloculus0-bot/BEAN/pull/51) remains open, so the candidate is not claimed as a merged Core upgrade.
- **Tested, but inconclusive transfer learning:** [Lab 023](docs/bean-causal-retention-lab023.md) persists generated lessons across a restart, then attempts fresh tasks with and without those lessons. A pilot scored 4 cold versus 6 retained holdout passes, but missing candidates and unmatched provider identity meant the independent judges classified it **INCONCLUSIVE**.
- **Lab 026 tests the memory hypothesis:** [Draft PR #96](https://github.com/danieloculus0-bot/BEAN/pull/96) implements four conditions using the **same real local Ollama model**: no memory, chronological history, evidence-ranked BEAN lessons, and an irrelevant-memory placebo. The author keeps candidate source and model receipts; credential-free Windows/Linux jobs check source hashes and independently grade generated code. [The first live pilot](https://github.com/danieloculus0-bot/BEAN/actions/runs/38181156634) has passed both protocol checks, with real-model evaluation still subject to its independent verdict. The experiment currently tests one evidence-memory component rather than all of BEAN. A repeatable causal learning advantage has **not** been established.

[**See this comparison on the homepage**](https://danieloculus0-bot.github.io/BEAN/#lab).

## Learning lab: experience, scoring and repeatable tests

**October 12, 2026 research status:** BEAN's existing Core on `main` already implements persistent evidence, review boundaries and audit trails. The newer **Sponge temporal-difference learner, scored compressed neural memories, and neuroevolution are in separate draft research PRs**, not silently deployed to Core `main`. The [public Learning Lab](https://danieloculus0-bot.github.io/BEAN/#learning) presents their measured experiments without inventing a production capability.

| Experiment | Measured outcome | Status and evidence |
| --- | --- | --- |
| **Sponge TD Q-learning in simplified Breakout** | On 200 untouched game seeds, a checkpoint chosen using separate validation games cleared **11.305 bricks/game vs 1.355 untrained** (**+9.95**), with **98.5% vs 0% game survival**. | Real BEAN Q-value updates, restartable hash-chain journal and scored checkpointing; [Sponge draft PR #99](https://github.com/danieloculus0-bot/BEAN/pull/99), [Windows/Linux CI and receipts](https://github.com/danieloculus0-bot/BEAN/actions/runs/38187025075). Both systems repeated the **same training seed and test sets**, not independent training-seed replications. |
| **Journal-backed independent Breakout prototype** | The separate tabular Q-learning study also demonstrated learning against a cold policy, but it does not by itself establish BEAN-wide self-improvement. | [Draft PR #98](https://github.com/danieloculus0-bot/BEAN/pull/98) and [test evidence](https://github.com/danieloculus0-bot/BEAN/actions/runs/38184219247). |
| **Deep Q-Network and inherited neural weights** | Real backpropagation, replay sampling, target networks, selection and mutation passed bounded Windows/Linux functional tests. | [Neuroevolution draft PR #107](https://github.com/danieloculus0-bot/BEAN/pull/107), [research methods and limits](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-deep-q-learning-20261012/docs/BEAN_NEUROEVOLUTION_20261012.md). Engineered three-value game observations, **not pixel Atari or general neural intelligence**. |
| **Can evolution beat an uninterrupted DQN?** | Initial independent training seeds **41–43**: evolved minus conventional DQN = **-4.53, -8.63, +0.82** bricks/game. New two-validation-cohort selection, on fresh seeds **44–46**: **-4.85, +0.23, +1.90** for the *raw evolved* candidates. | **No replicated evolutionary advantage.** The validation gate rejected the worse evolved model on seed 44 and retained the conventional learner. A fallback prevents some regressions; it is **not proof that the evolutionary algorithm learned better**. [Fresh comparison and artifacts](https://github.com/danieloculus0-bot/BEAN/actions/runs/38229337741) · [first failure report](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-deep-q-learning-20261012/docs/BEAN_NEUROEVOLUTION_FIRST_REPLICATION_20261012.md). |

**The memory principle:** Experiments assess utility *before* filing a checkpoint; candidate weights and quality metadata are preserved in compressed, SHA-256-verified memory records with a short mnemonic and a hash-chained journal. Weak attempts are retained as evidence, not silently accepted as better policies. A checksum proves **data integrity**, not source truth, statistical validity or improved intelligence. These scored capsules and learning loops still require independent qualification before any merge to Main.

**Next qualification gate:** multiple unseen training seeds and evaluation environments, equalized compute and game budgets, independent judging, durable score-and-lineage receipts and rollback on regression. A green workflow or a win over an **untrained** opponent is not evidence of superiority over a fully trained reference. This research cannot authorize trades, hardware actions or an autonomous production update.

## Start here: see BEAN do something useful

BEAN is not waiting for a robot body. The Core already has four actual behaviors wired into a single offline, reproducible acceptance command:

```bash
git clone https://github.com/danieloculus0-bot/BEAN.git
cd BEAN
python -m pip install psutil
python -m examples.capability_proof
```

The command uses **actual BEAN APIs** and temporary fictional data, not prewritten success narration. Its JSON result includes the pass/fail verdict, the behavior observed and clear limits; a failed assertion stops the run.

| Evidence-backed behavior | What the operator learns | Source |
| --- | --- | --- |
| **Real persistent continuity** | A recorded event and a pending-review proposal survive closing and reopening SQLite in two BEAN sessions | [Live code](examples/restart_continuity.py) · [Regression](bean/tests/test_restart_continuity_demo.py) |
| **Contradictions remain unresolved** | Two conflicting caller-supplied reports cannot be passed off as independently verified truth | [Evidence Bridge](bean/integration/evidence_bridge.py) · [Adversarial tests](bean/tests/test_evidence_bridge_contract.py) |
| **Claims and actions have boundaries** | Missing sources are flagged and a motion-style proposal is not authorized to execute | [Epistemic Guard](bean/cognition/epistemic_guard.py) · [Plugin tests](bean/tests/test_public_plugin.py) |
| **Missing does not equal zero** | A missing quality report returns N/A; a complete, host-attested report can legitimately say zero | [BEAN Watcher](bean/runtime/watcher.py) · [Missing/stale tests](bean/tests/test_watcher.py) |

[**Open the complete executable evidence ledger**](docs/VERIFIED_UTILITY_AND_EVIDENCE_2026-10-11.md). It labels which findings are stable Core code, separate Bridge integrations, experimental branches or inconclusive tests. Synthetic contract success is not measured workplace impact or general intelligence.

## Recent working skills: autonomy research and AIscend

- **BEAN Core autonomous engineering lab:** The scheduled [self-repair workflow](.github/workflows/bean-autonomous-selfrepair.yml) feeds independently witnessed failures to local Qwen or a free hosted model, accepts bounded AST-statement source edits, and demands matching Windows/Linux acceptance before attempting automatic promotion. Real model-authored proposals have been produced, but the [latest checked run](https://github.com/danieloculus0-bot/BEAN/actions/runs/38175931431) rejected an unchanged candidate and later lost inference. **No model-authored Core change from that run was promoted.** See [the author](bean/evaluation/autonomous_selfrepair.py) and [independent verifier](bean/evaluation/autonomous_selfrepair_verify.py).
- **AIscend five-minute market research:** The [research supervisor](https://github.com/danieloculus0-bot/AIscend/blob/main/src/bean_research_supervisor.py) uses newly closed five-minute Coinbase candles for experiments, while an independent hourly Strategy School continues on completed hourly bars. The [forward paper book](https://github.com/danieloculus0-bot/AIscend/blob/main/src/bean_five_minute.py) requires subsequent candle observations, next-bar paper fills, modeled costs, BTC comparison and at least 288 forward observations for grading. This is **not live trading profit evidence**.
- **AIscend optional local code engineer:** A separate [Windows Ollama workflow](https://github.com/danieloculus0-bot/AIscend/blob/main/docs/BEAN_UNATTENDED_LOCAL_ENGINEER.md) can test proposed edits in worktrees and adopt passing changes when explicitly started on the user's PC. GitHub research CI alone does not start this local workflow.
- **Public AIscend sample dashboard:** [The read-only demo](https://danieloculus0-bot.github.io/BEAN/aiscend.html) shows sample values only for fields in the real application (net liquidation, cash/USDC, P/L, wealth multiple and bankroll-doubling Game Score), existing research views, and separate public Coinbase last-trade quotes. It has **no fabricated $100 paper-buy/sell terminal**; the unrelated invented website widget was removed in [PR #109](https://github.com/danieloculus0-bot/BEAN/pull/109). Example research scenes are illustrative display states, not active trading controls; no wallets, trades or private account data are connected.
- **Bridge reproducible defect hunter:** [Synthetic invariant testing](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/docs/BEAN_METAMORPHIC_DISCOVERY_LAB.md) records seeded timezone, source-coverage and observation-order discrepancies. Findings are research witnesses, not automatic fixes.

## Verified engineering snapshot

On October 11, 2026, [Core's previous green four-platform regression](https://github.com/danieloculus0-bot/BEAN/actions/runs/38156840053) passed Windows and Ubuntu on Python 3.10 and 3.12. Its Ubuntu/Python 3.12 job reported **559 passed, one skipped, 47 subtests passed, and 84% measured code coverage**. These figures describe that exact commit and test suite, not a lifetime success count. The later October 12 [four-platform Core regression](https://github.com/danieloculus0-bot/BEAN/actions/runs/38243582120) and [AIscend site checks](https://github.com/danieloculus0-bot/BEAN/actions/runs/38243582034) also passed for the website-only correction in PR #109; that does **not** verify neuroevolution superiority or merge experimental code.

| Comparison | Actual finding | Scientific boundary |
| --- | --- | --- |
| BEAN vs Aider | Both passed **16/16** held-out functional tests | **TIE**, two synthetic coding tasks; [receipts](https://github.com/danieloculus0-bot/BEAN/actions/runs/38110050070) |
| Model-written selector repair | **14/14** development checks and **7/7** fresh holdout checks | Limited bounded source repair, not autonomous general software engineering; [study](docs/BEAN_LLM_REPAIR_EXPERIMENT_20261011.md) |
| Synthetic evidence-sensitive ranking | **91.25% vs 18.75%** on a deliberate source-echo benchmark | Bridge research, not live Google or browser superiority; [lab](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38029876766) |
| Five specialist competitors | **5 INCONCLUSIVE** in the October 12 rematch, with separate author and judge jobs | The specialist jobs did not produce valid comparable opponent submissions. BEAN did not beat OpenCode, Goose, OpenHands, Continue or Cline. The tournament did not use Sponge; [rematch evidence](https://github.com/danieloculus0-bot/BEAN/actions/runs/38187443602) |
| Arduino Nano and ESP32 | **2 CPU emulator targets passed**, plus 6,144 native fault transitions and a seeded E-stop mutation canary | [Bridge main lab](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/experiments/robot_motion/README.md); no physical motor control. ESP32 FreeRTOS logical watchdog tested; Wokwi NOT_RUN (missing token). [Fresh evidence](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38161744114) |

**Not proven:** AGI, consciousness, autonomous physical control, independently authenticated external truth, profitable trading, production ERP connectivity or universal coding superiority.

## The Core, Bridge and applications

```text
              HOST OBSERVATIONS, TASKS AND EVIDENCE
                               |
                   source + coverage contracts
                               |
                        BEAN CORE (main)
          +--------------------+--------------------+
          |                    |                    |
    SQLite continuity    Evidence/uncertainty   Local reasoning
    session and history   contradictions/N/A     optional Ollama
          |                    |                    |
          +--------------------+--------------------+
                               |
                  structured reviewable proposals
                               |
                      HOST OWNED AUTHORIZATION
                        (no implicit actions)
                               |
          +--------------------+--------------------+
          |                    |                    |
   BEAN AI Bridge         Host application      Optional robot
   offline KPI exports    or AIscend research   / controller
```

- **Core main:** memory, cognition, epistemic checks, host-neutral evidence review, watcher, scheduled tasks, Ollama reasoning adapter, Windows voice, review-only code proposals, SQLite engineering journal and a local four-tool MCP developer preview. A module being in Core does not imply that every feature is on by default.
- **[BEAN AI Bridge main](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-):** separate offline export adapters and a [Daily Exception Brief](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/docs/DAILY_EXCEPTION_BRIEF.md) that generates private HTML/JSON for OTD, overdue-work and RMA evidence. This is not an authenticated live ECI JobBOSS feed.
- **[AIscend](https://github.com/danieloculus0-bot/AIscend): working Coinbase crypto-trading beta.** AIscend implements live-capable Base wallet swaps and Coinbase Advanced spot orders, with persistent decision history and a reproducible Windows build. Its embedded BEAN-style memory records market predictions and outcomes; [Strategy School](https://github.com/danieloculus0-bot/AIscend/blob/main/src/bean_strategy_lab.py) performs chronological historical research; an optional [fresh-candle policy gate](https://github.com/danieloculus0-bot/AIscend/blob/main/src/bean_policy.py) can confirm or veto existing proposed buys. AIscend, not BEAN Core, executes exchange orders. Research-selected rules are not automatically installed as live strategies. [Successful Windows build](https://github.com/danieloculus0-bot/AIscend/actions/runs/38168385198). Profitability and complete fills/fee reconciliation remain unverified.
- **Research branches:** robotics, ESP32/Arduino emulation, peer-agent tournaments and many LLM experiments are recorded but are not silently imported into live systems.

## Consolidated engineering evidence inventory

BEAN's [read-only audit CLI](scripts/audit_research_inventory.py), consolidated from independently tested [engineering audit PR #81](https://github.com/danieloculus0-bot/BEAN/pull/81), enumerates Core and Bridge branches, pull requests, test modules, workflow files and Git ancestry in both JSON and Markdown:

```bash
python scripts/audit_research_inventory.py --output-dir audit-output
```

This command requires GitHub access (and may need a suitable read-only `GH_TOKEN` for higher limits), **never changes repository files**, and calls out incomplete inventories instead of claiming a clean sweep. Ahead/behind Git commits do not prove that a feature is missing from `main`: squash merges can hide that in ancestry. [Read its verification report](docs/ENGINEERING_VALIDATION_2026-10-11.md).

## BEAN inside ChatGPT — early MCP plugin preview

The public-source **[BEAN Evidence Companion](integrations/chatgpt/README.md)** now has a bounded, optional MCP implementation that calls real BEAN Core epistemic guard, evidence bridge, proposal filters, and SQLite restart-proof routines. Four read-only tools let a ChatGPT-compatible MCP client check the structure of claims, compare unverified reports, screen a proposal, and inspect BEAN's persistence demonstration.

**Status: developer preview.** The MCP server is runnable locally but **not hosted, submitted, reviewed, approved, installable or published** in ChatGPT yet. A stable HTTPS deployment, privacy controls, confirmed developer identity and OpenAI directory review are required. The plugin does **not** authenticate internet evidence or maintain a user's personal memory. No ERP, trading, robot or network actions are exposed.

## Local Ollama reasoning and GitHub engineering evidence

BEAN Core now supports an **opt-in local Ollama reasoning provider**. A running model supplies structured proposals; BEAN's persistent reasoning layer validates and journals the results. The model does not become BEAN's identity or inherit permission to execute commands. See [the live Ollama reasoning example](examples/ollama_reasoning.py) and [Windows voice-chat setup](docs/bean-local-voice.md).

A separate **[GitHub engineering evidence bridge](docs/bean-github-engineering-bridge.md)** reads repository branches, pull requests, and CI outcomes, retaining hash-chained receipts in BEAN's own SQLite journal. It can help identify failing checks and work needing review, but this v0.1 bridge itself does not merge code or issue remote commands.

These integrations are now included in `main`. Live Ollama performance and connected GitHub access depend on the local installation and authorization.

## Verify BEAN Core locally

**[Updated usefulness audit — what BEAN actually helps with, where it doesn't, and the next proof](docs/BEAN_USEFULNESS_AUDIT_2026-10-11.md)**

The standalone two-session persistence demonstration is available as `python -m examples.restart_continuity`; unlike the one-shot mock proposal quickstart, it explicitly verifies that the SQLite event and pending proposal survive a clean BEAN shutdown and reopen. It still uses a mock reasoning provider and temporary local data. The separate [Bridge Daily Exception Brief](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/docs/DAILY_EXCEPTION_BRIEF.md) now provides a practical, private, read-only management summary from authorized local export ledgers.


[![BEAN full core regression](https://github.com/danieloculus0-bot/BEAN/actions/workflows/brain-smoke.yml/badge.svg)](https://github.com/danieloculus0-bot/BEAN/actions/workflows/brain-smoke.yml)

**New to BEAN?** Start with the [offline quickstart](docs/GETTING_STARTED.md), [live project website](https://danieloculus0-bot.github.io/BEAN/), or [research evidence index](docs/experimental-research-index-2026-10.md).

The current host-neutral API can record a fictional observation in a disposable local SQLite database and produce a stored, review-required proposal using a **mock** provider:

```bash
git clone https://github.com/danieloculus0-bot/BEAN.git
cd BEAN
python -m pip install psutil
python -m examples.quickstart_reasoning
```

This is an executable architecture demonstration, **not** a demonstration of trained-model intelligence or unsupervised autonomy.

**Want to follow BEAN's development?** Visit the [mint-green site](https://danieloculus0-bot.github.io/BEAN/#start), star/watch the repo if you find it useful, or [report what you can reproduce](CONTRIBUTING.md). The [launch kit](docs/LAUNCH_KIT.md) contains shareable, evidence-checked announcements and the independent test references.  The [BEAN AI Bridge](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-) provides separate generic ERP/evidence adapters and synthetic replay. See the [public discovery and GitHub Pages activation checklist](docs/PUBLIC_DISCOVERY_LAUNCH.md). Source visibility alone does not provide a redistribution license.


## How to verify a candidate before promoting it

1. Start with a reproducible user benefit or failure, not a synthetic score.
2. Pin exact source code and input fixture digests; never use holdout answers to tune the candidate.
3. Preserve negative and inconclusive findings, including provider errors and missing data.
4. Execute independent regression and adversarial tests, preferably on Windows and Ubuntu.
5. Incorporate only genuinely new reusable behavior into Core. Leave domain-specific adapters in Bridge or their host project.
6. Review the permissions and operational boundary before merging. No algorithm may approve its own unsupervised production deployment.

The [utility and scientific evidence ledger](docs/VERIFIED_UTILITY_AND_EVIDENCE_2026-10-11.md) provides concrete examples of this standard. The next valuable operational validation is an authorized, ten-workday shadow trial of the offline quality exception report, measuring time saved **and** unsupported-claim rate. That business result has not yet been measured.

## What BEAN does

Most software starts each decision with whatever state the application explicitly hands it. Most AI systems are extremely capable reasoners but are only as good as the context, evidence, memory, boundaries, and feedback around the current request.

BEAN exists to supply that missing structure.

    observations / events / evidence
                 |
                 v
       persistent BEAN state
                 |
       +---------+---------+
       |                   |
       v                   v
    deterministic       optional reasoning
    logic / rules        providers / models
       |                   |
       +---------+---------+
                 |
                 v
        hypotheses / proposals
                 |
                 v
      policy + capability boundaries
                 |
                 v
       host / service / effectors
                 |
                 v
              outcomes
                 |
                 +------> BEAN

The loop matters more than any one model. A stronger model can improve BEAN's available reasoning horsepower, but continuity, evidence, contradiction handling, uncertainty, history, policy, and learning do not disappear when the model changes.

## One architecture, several lives

BEAN is intentionally body-optional and provider-optional.

- **Standalone:** BEAN can maintain its own runtime, memory, world state, reasoning cycle, and bounded capabilities.
- **Embedded:** another project can use BEAN as its persistent reasoning and continuity layer.
- **Service:** multiple tools or applications can submit events and reasoning requests to the same governed BEAN instance.
- **Embodied:** sensors become inputs and physical systems become effectors. The body is a host, not the identity.
- **Multi-model:** language models, deterministic engines, local models, or future reasoning systems can be treated as replaceable cognitive resources rather than BEAN itself.

Execution is always a separate architectural concern from reasoning. In an embedded deployment the host may own execution. In a standalone or embodied deployment, explicit effectors and policy boundaries may own execution. A reasoning provider never gets a magical direct wire to the outside world.

## Core behavior

BEAN is being built around a small set of durable behaviors:

- Persistent local continuity instead of disposable prompt state.
- Evidence lineage and traceable context.
- Versioned self and world claims.
- Explicit uncertainty instead of forced certainty.
- Hypotheses that remain hypotheses until evidence changes them.
- Contradiction detection, review, and repair.
- Significance and attention so everything is not treated as equally important.
- Associative memory and wisdom traces without pretending associations are facts.
- Relationship and trust models grounded in evidence.
- Bounded context construction for external reasoning providers.
- Structured proposals that can be inspected before anything acts on them.
- Outcome history that can change future trust, assumptions, and reasoning.
- Self-improvement proposals with explicit benefit, cost, risk, validation, and rollback.

## Current implementation

| Capability | State |
|---|---|
| Persistent SQLite memory, sessions, events, continuity records | Implemented |
| Versioned identity, boundaries, capabilities, self/world claims | Implemented |
| Significance, surprise, preferences, drives, goals, consolidation | Implemented |
| Epistemic guard, contradiction court, falsification | Implemented |
| Uncertainty garden, hypotheses, evidence levels, review records | Implemented / evolving |
| Wisdom traces, repair records, loop signatures | Implemented / evolving |
| Relationship history and evidence-weighted trust | Implemented / evolving |
| Bounded reasoning context and replaceable provider adapters | Implemented / evolving |
| Structured reasoning proposals and proposal persistence | Implemented / evolving |
| Supervised self-optimization records and rollback planning | Implemented / evolving |
| Standalone runtime, inbox, system monitoring, durable state | Implemented |
| RAM-backed BEAN Watcher, configurable recall and N/A-aware source status | Implemented as opt-in local report adapter |
| Host-neutral evidence/uncertainty bridge and scheduled independent-source review | Implemented, Bridge smoke-verified (host-attested evidence; opt-in) |
| Generic host integration | Active development |
| Tabular Sponge TD Q-learning and score-before-filing compressed memory | **Experimental PR #99; not merged to `main`** |
| PyTorch DQN, replay and weight-inheriting neuroevolution | **Experimental PR #107; not merged to `main`** |
| Physical embodiment | Optional future host |

BEAN is developed against real host projects and changing domains rather than being designed as a sealed demo. The architecture is expected to keep evolving as those deployments expose better abstractions.

### Core ↔ Bridge evidence-continuity smoke

A [host-neutral evidence cycle](docs/EVIDENCE_BRIDGE_READINESS.md) connects typed
external source observations to BEAN Core's actual SQLite memory, uncertainty
garden and epistemic audits. A host can optionally schedule **bounded**
read-only review using BEAN's existing durable TaskEngine. Revisions,
contradictions and restart continuity are verified using a separate
[Bridge cross-platform smoke branch](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/smoke/core-evidence-contract-20261010).
A declared source or verification ID is **host-attested**, not independent
authentication or proof of truth. No new physical or financial action is enabled.

## Research experiments and published findings (not all merged)

BEAN is being evaluated through **reproducible, isolated experiments** in evidence reliability, uncertainty reasoning, model revision, confidence-directed search, and lifelong empirical learning. The research code remains on experimental branches; documentation here does **not** mean those features are merged or production-ready.

**[Read the research index: findings, limitations, source branches, test runs and downloadable output artifacts](docs/experimental-research-index-2026-10.md)**

| Experiment | View experiment and output |
| --- | --- |
| **Evolution and source reliability** | [Lab 001 research branch](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/experiment/bean-evolution-lab-20261009) · [Simulation report and tests](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/37995651207) |
| **Evidence Intelligence / competing hypotheses** | [Lab 003 findings](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-evidence-intelligence-20261010/experiments/evolution_lab/LAB003_FINDINGS.md) · [JSON/test output](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38028778085) |
| **Learning when previous trust becomes wrong** | [Lab 004 findings](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-model-revision-lab004-20261010/experiments/evolution_lab/LAB004_FINDINGS.md) · [Cross-platform results](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38029372008) |
| **Confidence-directed search and page reranking** | [Lab 005 source](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/experiment/bean-confidence-search-lab005-20261010/experiments/search_lab) · [Ranking results](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38029876766) |
| **Nonterminal learning and cross-abstraction relevance** | [Lab 006 research record](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-epistemic-continuity-lab006-20261010/experiments/search_lab/LAB006_CONTINUOUS_LEARNING.md) · [100-test run and output](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38030419931) |

**Key result:** Empirical conclusions can be temporarily settled without blocking future observations. In the synthetic studies, confidence-driven investigation improved some outcomes but also exposed failure modes: stale learned trust, source-echo duplication, inspection expense, and regressions under changed conditions. **These are not live-browser benchmarks or evidence of AGI.** Exact caveats and comparative metrics are in the [research index](docs/experimental-research-index-2026-10.md).

## Origin, quickly

BEAN began as the operating brain for a future robot.

That immediately forced a harder question than locomotion: what should persist when the model changes, how should evidence be remembered, how should uncertainty survive, how should contradictions be handled, and how can a system improve without rewriting its own history?

The reasoning architecture became more useful than the original body constraint. BEAN therefore evolved from **a brain for one robot** into **a universal persistent reasoning architecture that can inhabit software, workflows, services, machines, or a body**.

The robot is still invited. It just no longer gets to define the project.

## Operating principles

    Evidence before belief.
    Preserve uncertainty until evidence resolves it.
    Contradictions are information, not inconveniences.
    Memory is continuity, not identity theater.
    The LLM is a reasoning resource, not BEAN's identity.
    Reasoning and execution remain separable.
    Capabilities must be explicit.
    Actions must be attributable.
    Outcomes must come back into the system.
    Improvement should be inspectable and reversible.
    Never invent success.
    Keep receipts.

## Why this exists

Powerful reasoning should not require a giant organization, a giant software stack, or a giant consulting budget.

A small manufacturer, an autonomous research project, a quality system, a maintenance platform, a market agent, or a future machine can all benefit from the same underlying thing: a system that remembers what happened, understands what it knows, admits what it does not know, connects consequences across time, and gets less stupid from experience.

That is the job.

**BEAN does BEAN.**

## BEAN Watcher

Native BEAN Watcher connects authorized normalized report exports to BEAN's working memory and append-only event ledger. Reports lacking an explicit completeness assertion, required metrics or evidence references show **N/A**, not zero. Change events wake it early; a configurable recall interval still rechecks unchanged sources. Historical values are retained separately, never passed off as current results. See [Watcher contract and example](docs/bean-watcher-contract.md). No live ERP credentials are included.

## Repository orientation

The current codebase includes persistent memory, cognition, world/self modeling, epistemic controls, reasoning adapters, hypotheses, wisdom, relationships, self-optimization, runtime services, and early embodiment support.

One current standalone deployment target is the NVIDIA Jetson Orin Nano Super Developer Kit because embodiment was BEAN's original proving ground. Jetson support remains useful, but it is a deployment profile rather than the definition of the architecture.

Persistent runtime data should remain outside the repository:

    BEAN_DB_PATH=/home/bean/bean_data/bean_memory.db
    BEAN_INBOX_DIR=/home/bean/bean_data/inbox

Jetson installation:

    bash install/jetson_brain_install.sh
    bash scripts/bean_doctor.sh

For non-Jetson development:

    BEAN_ALLOW_NON_JETSON_INSTALL=1 bash install/jetson_brain_install.sh

## Evidence-pinned peer review and safe code drafts (opt-in)

The [peer development protocol](docs/bean-peer-development-lab017.md) provides reusable Python objects for **immutable, digest-linked selector/builder/validator review messages** and *disposable* code-change proposals pinned to a source SHA and original content hash. It detects reordered receipts, orphan test results and modified source before creating a preview. No module automatically runs generated code, signs off a change, merges branches or grants production permissions.

`from bean.optimization.peer_dialogue import PeerDialogue, PeerMessage` and `from bean.optimization.code_candidate import draft_candidate` expose these review-only primitives. SHA256 integrity is not identity verification: the host must independently check CI results, repository access and trusted evidence origins. See [regression tests](bean/tests/test_peer_dialogue_lab017.py).

## Development direction

The near-term work is organizational as much as additive: make BEAN's persistent reasoning primitives easier to understand, isolate from old embodiment assumptions, and reuse without copying logic into every new project.

Priority direction:

1. Keep the reasoning core independent of any one body, UI, model provider, or domain.
2. Stabilize event, evidence, context, proposal, outcome, capability, and policy contracts.
3. Make project-specific behavior adapters around the core instead of forks of the core.
4. Preserve project-local memory while supporting deliberately shared context where appropriate.
5. Turn live outcomes into better calibrated trust, hypotheses, causal understanding, and improvement proposals.
6. Keep embodiment as a first-class host without allowing embodiment to become BEAN's identity.

BEAN is not finished. It is also no longer waiting for a body to become useful.

## Opt-in durable task behaviors

The native BEAN task engine runs only when a trusted local `BEAN_TASK_CONFIG` file is supplied. It persists bounded, named tasks and execution receipts in the existing SQLite memory store, marks interrupted or unverifiable work as **unknown / needs review**, and will not silently retry unknown side effects. The current allowlist contains only local integrity checks, report Watcher inspections, inner-weather updates, and relationship-summary maintenance; no shell, arbitrary Python, network effects, trades, email, or motors. The scheduler is **disabled by default**, and its human-review workflow and unattended-service readiness are still future work. See [durable-task contract and configuration](docs/bean-durable-tasks-lab011.md).

## Offline capability exam and non-fabricated baselines

The optional [BEAN evidence-first entrance exam](docs/bean-entrance-exam-lab012.md) provides seven reproducible fictional cases for unknown handling, verified citations, corrections, read-only probe requests, and limited cross-domain transfer. The bundled `MockLLMAdapter` is expected **not to pass** these capability criteria; fixture test doubles validate the examiner itself, never BEAN intelligence. Real capability improvements must be measured on independent unseen data with source audits. Run `python -m bean.evaluation.entrance_exam` to reproduce the honest baseline without network, private inputs, or hardware.

## Embedded host-neutral reasoning interface

`from bean.integration import BeanReasoningLayer` exposes a small Python lifecycle interface that records host observations, builds bounded reasoning context, and returns **review-required, stored proposals**, not actions. The mock provider works offline and a host must own permissions, execution, project isolation and authenticated input. Use **one BEAN memory store per host process**, avoiding concurrent use of the process-level singleton. See [host-neutral reasoning guide](docs/general-reasoning-layer.md). This is an optional API, not a claimed general intelligence system.

## Offline research evaluation harnesses (not deployed intelligence)

Core includes opt-in synthetic evaluation modules for [supervised source calibration](docs/bean-composite-growth-lab013.md), [read-only investigation and restart retention](docs/bean-investigation-retention-lab014.md), and [symbolic LLM-style provider emulation](docs/bean-simulated-llm-lab015.md). These run only when invoked, use fictional data and isolate their SQLite state. **Fixture gains do not demonstrate neural-model learning, open-ended self-improvement or production autonomy.** The incomplete hosted Lab016 remains isolated; no real hosted-model capability has been promoted. Their purpose in `main` is reproducible falsification of future changes.
