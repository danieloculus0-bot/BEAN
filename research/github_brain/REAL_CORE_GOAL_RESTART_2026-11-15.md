# Real NativeReasoningService and GoalCycle restart test, November 15, 2026

BEAN CONTEXT ACK v1

- Task: replace the fake reasoning-service-only GoalCycle regression with a disposable, real Core symbolic learning and restart test.
- Sources inspected: AGENTS.md, docs/AI_GATEKEEPER.md, docs/SOFTWARE_AUDIT_SKILL.md, docs/OPEN_AGENT_PATTERNS_2026_11_14.md, canonical origin record, continuity audit, research/github_brain/manifest.json, GOAL_REPETITION_2026-11-15.md, DEFAULT_NATIVE_GOAL_EXPERIMENT_2026-11-15.md, bean/learning/reasoning_service.py, bean/learning/local_reasoner.py, bean/learning/experimental.py, bean/runtime/goal_cycle.py, bean/runtime/digital_experiment.py, bean/tests/test_digital_experiment.py, and merged PRs #375/#376.
- Ledger: manifest generation 50, 50 boots, 1,672 events; receipt c50540e6d773d2abe019edd4e342e5effe7aa30bc2e42264c9c0c11ed5302c44; candidate and grammar-matched/passive 144/144. This new test uses separate disposable SQLite databases and never changes the GitHub checkpoint.
- Prior evidence: PR #376 reported 16 successful exact-head workflows, but its test used a fake service. This change has **not** yet passed exact-head CI.
- Minimum change: one focused integration test, no runtime behavior change, no new backend, no model provider.
- Unknown: exact-head test/CI outcomes; complete integrated cognitive adaptation on diverse tasks and strong baselines remains unproven.

The test uses the real NativeReasoningService with the existing ExperienceBank SHA journal, a cold-start matched control, three synthetic development examples, a withheld ordering question with independently computed deterministic oracle, real GoalCycle proposal/outcome persistence, and reopened SQLite stores. It asserts no automatic replay, a second and third unseen question solved after reopening, and explicit **unverified** GoalCycle outcome status. The cold-start control must abstain.

Falsifiers: rule fails to survive restart, cold-start solves without evidence, GoalCycle replays a completed proposal, withheld answer differs from independent oracle, or unverified comparison is promoted to verified success. This demonstrates only a narrow symbolic task family if green, not AGI, independent broad transfer or consciousness.

Local Git checkout unavailable because github.com DNS resolution failed. Thus **HOURLY COGNITIVE SIMULATION NOT RUN** and the new test is committed but not claimed executed. Next: exact-head CI, fix any failing tests, independently inspect diff/privacy, then integrate if gates pass. Subsequently add fresh multiple-rule/contradiction and equal-budget held-out evaluations. No new automation or private memory publication.
