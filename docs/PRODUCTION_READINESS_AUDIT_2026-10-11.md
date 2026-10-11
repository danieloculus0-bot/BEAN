# BEAN production-readiness audit and release gates

**Audited:** October 11, 2026. **Scope:** [Core main](https://github.com/danieloculus0-bot/BEAN) and [Bridge main](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-), source, test contracts, GitHub CI and documented host boundaries. This is a source/CI audit, **not** an onsite penetration test, physical hardware acceptance, verified uptime measurement, customer ERP trial or financial audit.

## Release judgment

**General-purpose autonomous production deployment: NOT READY.** BEAN has a functioning, actively tested developer/experimental foundation. Evidence supports specific Core software contracts and isolated Bridge simulations; it does not establish an operationally safe autonomous service. Only human-approved, read-only pilots with a documented local rollback path are candidates for tightly scoped deployment.

Do not translate GitHub workflow green to an SLA, authentic evidence, general intelligence, profitable strategies or physical safety certification. The [Core regression](https://github.com/danieloculus0-bot/BEAN/actions/runs/38162327923) passed four Windows/Ubuntu Python configurations. The [Bridge motion emulator regression](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38162127886) passed native C, AVR/simavr and ESP32 QEMU. Wokwi was NOT_RUN_MISSING_TOKEN; no motors were operated.

## Threat model and prioritized weaknesses

| Priority | Risk / failure mode | Observed evidence | Proposed acceptance gate | Disposition |
| --- | --- | --- | --- | --- |
| **P0** | SQLite event committed but JSONL append fails; local package path mixes independent DBs, and restarts do not reconcile | [Original `event_logger.py`](../bean/memory/event_logger.py); [engineering audit](ENGINEERING_VALIDATION_2026-10-11.md) | Crash/fault-injection + tamper tests; per-DB log path; restart recovery; two Python writers; cross-platform CI | **Fix in this audit PR**, subject to CI and explicit merge |
| **P0** | Physical actuation without independent power cutoff or tested motor safety | [Bridge MCU lab](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/experiments/robot_motion/README.md) implements logical interlocks only | Independent hardware E-stop/power removal, fault injection at real pins, brownout, stuck-pin/relay and wiring faults, tested human override | **Unmet: prohibit real motor integration** |
| **P0** | External evidence is host-attested; forged source labels, correlated reports or fabricated CI receipts could be promoted as verified | [Core Evidence Bridge](EVIDENCE_BRIDGE_READINESS.md) explicitly depends on authentic host verification | Signed provenance, verified host identity/authorization, replay boundaries, correlation/poisoning challenges, durable evidence revocation | **Unmet: do not auto-adopt external claims** |
| **P0** | An LLM-generated proposal might acquire unintended host privileges | [Core developer MCP](../integrations/chatgpt/README.md) is read-only; capability proposals and agent claims are not independently authenticated | Narrow signed action permits, enforce effects in host not prompt, least-privilege sandbox, adversarial command/tool tests; zero unauthorized action | **Not cleared for autonomous external action** |
| **P1** | SQLite load, multi-process lifecycle, backup consistency, disk-full response, migration and restore are under-tested | SQLite WAL + thread-local connection; no operational recovery drill documented | Crash-injection, backup/restore RPO/RTO demonstration, 24-hour stress, migration down/up, readonly/low-disk handling, clean account isolation | **In progress; broad validation outstanding** |
| **P1** | ESP32 command auth, packet framing, reboot replay and real watchdog scheduling unverified | [Emulator lab known gaps](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/experiments/robot_motion/README.md) | CRC/framing/fuzz, authenticated session epoch, stale packet denial after reboot, measured deadline with independent timer | **Unmet: logical emulation only** |
| **P1** | Meaningful utility and baseline superiority not shown on unseen workloads | [Usefulness audit](BEAN_USEFULNESS_AUDIT_2026-10-11.md), [benchmark caveats](VERIFIED_UTILITY_AND_EVIDENCE_2026-10-11.md) | Preregister benchmark, compare matched retrieval/model baselines, shadow workday reports with human time/error measures | **Unmeasured outside synthetic contracts** |
| **P1** | No demonstrated hosted service durability, incident response, independent secret scanning, SLOs, per-tenant data authorization or deployment/rollback | GitHub CI tests individual Python contracts, not supported service operations | Defined release artifact and SBOM, dependency scanning, hardened secrets, health/backup dashboards, incident/rollback rehearsal | **Unmet: developer preview only** |

## P0 memory-mirror hardening included in this proposed change

Current legacy design commits the SQLite row and separately appends JSONL to a package-relative `bean/logs/events.jsonl`. Losing the second write can make an already-persisted event appear to have failed or disappear from the human-readable audit trail.

The patch adds `bean/memory/audit_mirror.py` and changes `log_event` / `init_store` to:
1. Place JSONL at `<absolute-database-path>.events.jsonl`, so independent deployments do not mix journals or require package-write access.
2. Acquire an OS advisory lock around reconciliation and reread committed SQLite rows *after* locking. Linux uses flock; Windows uses msvcrt byte locking.
3. Compare all existing complete JSONL lines against canonical SQLite event rows; an altered or orphaned record **fails closed** rather than rewriting the offending historical file.
4. Recover a missing sidecar or a final byte-truncated line via fsynced, same-directory atomic replacement. Existing complete prefixes are extended only with missing rows and fsynced.
5. Preserve committed SQLite rows on mirror I/O failure and raise a descriptive `AuditMirrorError` carrying the already-committed event identity; **callers must never blindly retry the event**.
6. Reconcile on every database initialization, including after a process crash between the SQLite commit and mirror write.
7. Add regression probes for intentionally unavailable mirror I/O, partial tail, tampering, deleted sidecar, separate DBs, orphan line and two real concurrent Python processes. Require these across Windows and Ubuntu in Core CI.

**Explicit technical limitation:** O(n) prefix comparisons per new event (total high-volume cost can be O(n²)), no cross-host distributed lock, no cryptographic authenticity/immutable/WORM journal, no automatic migration or reconciliation of the *old package-global JSONL*, no proof against hostile control of both DB and mirror, and no unclean power-loss guarantee with SQLite `synchronous=NORMAL`. This is a correctness and recovery improvement, **not a statement of fully production-hardened audit durability**. A throughput/multi-host redesign is still a release gate.

## Production-readiness acceptance milestones

1. **Read-only pilot:** test installation with disposable/approved datasets; stable config, filesystem permissions, fail-closed response, no external actions, audited job IDs and easy operator rollback. Prefer the existing Bridge Daily Exception Brief and Core receipt demos.
2. **Persistent host:** external independent tests for SQLite backup/restore, schema upgrades, power cut, disk full, corruption, restart, multi-process contention and tamper notification. Required before relying on persistent learning across unattended deployments.
3. **Model/evidence:** authenticated source provenance, red-team source spoofing and correlation, blind matched-input quality benchmarks, confidence/abstention calibration, and explicit uncertainty on missing data.
4. **Autonomous software changes:** pinned immutable candidate, hidden external holdouts, artifact integrity, signed/reproducible tester receipts, no self-approval or automatic production promotion.
5. **Physical autonomy:** separately reviewed robot controller, hardware-enforced fail-safe, verified watchdog, operator override, thermal/battery/power monitoring, real sensor testing, field test plan and independently recorded results.

Release claims must point to exact workflow run SHA and artifacts. **No evidence** is an explicit unknown, not a simulated pass.

## Owner/reviewer checklist

- [ ] CI green on the exact hardening PR SHA, including separate Windows and Ubuntu memory recovery and multi-process adversarial tests
- [ ] Confirm modified README and operator instructions match the merged `main` behavior
- [ ] Check real filesystem permission model and backwards-compatibility needs for any existing package-global JSONL files
- [ ] Test backup/restore under actual power-failure and storage-pressure conditions
- [ ] Harden and verify authorized host-to-BEAN credentials before a network service
- [ ] Verify hardware physical E-stop outside the simulator before connecting motors
- [ ] Execute a measured, permission-approved ten-day human-shadow usefulness pilot
- [ ] Repeat this audit after every production-affecting capability promotion
