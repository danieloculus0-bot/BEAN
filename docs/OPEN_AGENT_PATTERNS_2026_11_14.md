# Open agent patterns integrated into BEAN Core: November 14, 2026

## Verified licenses and design provenance

The original AutoGPT Classic agent, https://github.com/Significant-Gravitas/AutoGPT/tree/master/classic/ , is MIT-licensed. Its iterative plan/action/feedback design informed this BEAN change. The separately licensed modern autogpt_platform is excluded. No upstream implementation was copied.

Other design references to study and compare, NOT integrations in this patch:

- Letta Code (Apache 2.0): durable identity and evolving agent memory.
- LangGraph (MIT): checkpointed execution and resumption.
- OpenHands (MIT core): real action execution and software evaluation.
- OpenCog Hyperon (MIT): symbolic knowledge structures.
- Omega (Apache 2.0): reasoning and persistent cognition.
- Mem0 (Apache 2.0): semantic recall and memory consolidation.
- CAMEL (Apache 2.0): synthetic multi-agent experience.

Upstream source reuse requires retaining relevant license notices. This feature contains original BEAN code and does not bundle third-party dependencies. BEAN currently has no declared outbound license.

## Actual integrated feature

The original cognition GoalStateEngine persists goals. The new GoalCycle operates on those existing goals and the original SQLite store. It chooses by priority, experience novelty and observed action-outcome history, then atomically claims a goal and records its choice before execution.

The host supplies callable capabilities, and the default runtime registers actual internal model updates and reflection. Unknown or unavailable operations stay pending, missing evidence is never promoted to success, and interrupted actions are never automatically replayed. Each outcome is persisted with a receipt and appears in the standard BEAN observation stream.

This is an actual internal autonomous execution and selection loop, not a general-purpose open-world agent, consciousness proof, automatic neural weight update, or claim of independently verified gains. It does not run unrestricted model-authored commands.

Runtime: BEAN_GOAL_CYCLE=1 by default; BEAN_GOAL_CYCLE=0 disables. Goals are created by normal cognition consolidation; an empty queue means no synthetic action. BEAN's regular task engine and research ledger remain separate and intact.

## Tests

Run: python -m pytest bean/tests/test_goal_cycle.py bean/tests/test_task_engine_lab011.py bean/tests/test_task_adversarial_lab011.py -q

Tests cover persisted execution across restarts, no replay on crash, failure and Unknown/N/A distinctions, novelty-based selection, unregistered capabilities staying pending, and tick-handler integration. GitHub workflow runs targeted tests on Linux and Windows.

Future work: add explicitly registered real digital experiments, standardized multi-step tool plans, measured external benchmark feedback and held-out comparisons against the unmodified BEAN Core. None are asserted complete here.
