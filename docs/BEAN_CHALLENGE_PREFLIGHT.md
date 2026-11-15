# BEAN challenge preflight v1

**Scope:** a testable **BEAN Core local check**, not GitHub branch protection, an independent truth verifier, a new learner, or an autonomous critic.

## What it does

BEAN's existing SQLite store now holds `challenge_reviews`, `challenge_objections`, and `challenge_overrides`. Every decision binds an action, target, revision and summary to a SHA-256 proposal fingerprint. Objections require a readable reason and existing receipts from BEAN's `epistemic_audits`, `claim_conflicts`, or `claim_verdicts` tables. Unknown evidence references are rejected, not invented. The objection and receipt IDs persist even after an override.

A recorded **BLOCK** stays in force on subsequent checks of the exact proposal, even if the caller submits an empty objection list. Explicit `override` changes the effective decision to **OVERRIDDEN** without erasing or editing the objection. A fresh objection after an override creates a fresh blocking challenge. A revision change is a new proposal.

## Using the local gate

Run against an **existing** BEAN Core SQLite DB. Create `proposal.json` with the following shape and replace the placeholder with an actual existing Core audit/conflict/verdict ID:

```json
{
  "proposal": {
    "action": "merge",
    "target": "owner/repository#123",
    "revision": "exact-candidate-commit-sha",
    "summary": "Promote a specific tested source revision"
  },
  "objections": [
    {
      "kind": "conflict",
      "reason": "Recorded failed regression conflicts with this promotion",
      "evidence_refs": ["epistemic_audit:EXISTING-AUDIT-ID"]
    }
  ]
}
```

```bash
python scripts/bean_challenge_preflight.py --db /path/to/bean_memory.db review --request proposal.json
# The review prints a challenge_id; exit 2 means BLOCK.
python scripts/bean_challenge_preflight.py --db /path/to/bean_memory.db status --challenge-id CHALLENGE_ID
python scripts/bean_challenge_preflight.py --db /path/to/bean_memory.db override --challenge-id CHALLENGE_ID --actor OWNER --justification "Why proceed despite the objection"
```

Exit 0 means this CLI's reviewed decision permits the proposed action; exit 1 means invalid/unavailable input; exit 2 means blocked. **Every effectful caller must check the exit code and refuse the action on 1 or 2**. BEAN cannot stop callers that bypass this CLI. The override actor is **caller supplied and not authenticated by Core**: an external host must authorize the person requesting it. Receipt existence is verifiable in SQLite, but neither the truth nor relevance of the cited claim is independently authenticated.

BEAN's existing Epistemic Guard and Contradiction Court remain the producers of evidence. This first increment does not automatically decide which claim is relevant to which merge. A caller or future integration must retrieve relevant evidence and formulate objections; do not label an empty-objection ALLOW as independent critical analysis.

## Regression criteria

`python -m unittest bean.tests.test_challenge_gate -v` tests valid receipts, unsupported citations, persistence across new gate instances, an unerasable block, override audit history, new objections following override and exact revision binding. GitHub Actions runs this contract for changes to the gate. **A passing test does not prove it is enforced on all repository merges.** This repository does not currently have an enforced branch ruleset for this feature.

## BEAN CONTEXT ACK v1

- Task: evidence-backed objections, hard-stop decisions and recorded human override.
- Reused: `bean/memory/store.py`, `bean/cognition/epistemic_guard.py`, `bean/cognition/contradiction_court.py`, `memory/identity/origin_record.json`.
- Ledger and scoreboards: reviewed the generation-51 continuity audit; individual trial archive and evidence relevance were **not independently verified**. The `research/PERSISTENT_LEDGER.md` path is absent on current `main`.
- Current evidence: remote source review from GitHub `main`; tests on the proposed branch must be evaluated at the exact commit.
- Unknowns: current CI result until the PR workflow completes; external GitHub rule enforcement; actor authentication.
- Minimum change: existing-Core SQLite tables, API/CLI, seven regression tests and a scoped CI job.
- Runtime change: a caller-invoked block/override check only; no modification to the origin covenant or BEAN's autonomous research policy.
