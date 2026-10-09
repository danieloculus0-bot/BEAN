# BEAN comprehensive capability audit, 2026-10-09

Status: **experimental branch only**. Do not merge without review of behavioral changes.
Branch: `experiment/bean-capability-lab-20261009`.
Production/default branch remains unchanged.

## Executed evidence

- Initial complete pytest discovery: 109 collected, 107 passed, 2 failed; pre-fix coverage 78%.
- Latest expanded suite: **126 passed**, **82% aggregate coverage** on Ubuntu Python 3.10.
- Cross-platform matrix completed successfully on Ubuntu 3.10, Ubuntu 3.12, Windows 3.10 and Windows 3.12.
- CI: https://github.com/danieloculus0-bot/BEAN/actions/runs/37995082054
- Independent BEAN AI Bridge evolution study is in the separate bridge repository, on its own experimental branch.
- All tests were offline/synthetic. They do not constitute real sensor, actuator, hosted LLM, ERP, or embodiment validation.

## Defects found and addressed on this branch

1. **Origin version drift**: boot readiness expected origin covenant 001 when the canonical origin module writes 002. The check now derives the required version from `ORIGIN_KEY`.
2. **Origin event description drift**: canonical audit record now explicitly identifies the origin covenant.
3. **Obsolete memory identity assertion**: the test expected development stage `memory-core-0.1` while the current bootstrap identifies `brain-first-bootable-0.13`.
4. **Preference learning could never mature from incremental outcomes**: subthreshold outcomes were discarded before the minimum evidence count was reached. Pending evidence is now durable but remains inactive, duplicate references are ignored, and a preference only activates after threshold evidence.
5. **Invalid model confidence could propagate NaN**: reasoning response parser now rejects non-finite confidence values rather than treating them as valid.

## Test depth added

- Attention prioritization and open-question matching.
- SQLite wisdom association traversal, weight filtering and depth bounds.
- Body config structural error reporting.
- Evidence-driven preference maturation, duplicate protection, and activation threshold.
- Optimization proposal approvals, validation outcomes, and audit records; never auto-executed.
- Origin version contract.
- Offline OpenAI adapter success/error paths with intercepted requests.
- Reasoning parser corruption/finiteness guards.
- Restart continuity, session closure, and identity recovery.

## Known incomplete validation and next priorities

- **Real embodiment**: motion simulator and safe-command unit tests exist. Actual power, interlocks, motors, bus failures, watchdogs and E-stops require hardware verification and are not certified by CI.
- **Live reasoning provider**: only mock transport and offline tests were run. No live API request was made.
- **Low-coverage integration**: runtime bootstrap/inbox orchestration, monitoring error branches, motion safety edge cases, speculative hypothesis review, and some cognition maintenance branches need deeper adversarial and fault-injection tests.
- **Cognitive generalization**: passing scripted tests does not demonstrate autonomous curiosity or subjective consciousness. Generalization should be tested on unseen tasks and adversarial signals.
- **Governed self-modification**: the optimization governor remains a proposal and audit layer. Experimental mutation and evaluation should be isolated in a separate runner with hidden test data, resource limits and no physical/network effectors.

## Merge decision

This branch is a research candidate. Review preference persistence semantics and compatibility with any existing production memory database before promoting the changes to main. Do not interpret overall test coverage as an exhaustive safety guarantee.
