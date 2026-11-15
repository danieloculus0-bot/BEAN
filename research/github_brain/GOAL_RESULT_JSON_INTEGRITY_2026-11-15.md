# GoalCycle durable result JSON integrity, 2026-11-15

BEAN CONTEXT ACK v1. Reviewed AGENTS.md (blob 5b9714e), docs/AI_GATEKEEPER.md (174e302), docs/SOFTWARE_AUDIT_SKILL.md (f103ae4), docs/OPEN_AGENT_PATTERNS_2026_11_14.md (f33d650), canonical origin (6ec1548), origin loader (89d92bd), GoalCycle (e682729), tests (28474a3), prior repetition handoff (2301d60), and current generation-50 manifest (c02ec5a). Authenticated GitHub lists 24 owner repositories. PR #373 is already merged into main at edbee2bcf0ebff97ed757bf36a4048c316f722af; do not repeat its SHA linkage work.

## Observed deficiency and alternatives

The existing GoalCycle persisted json.dumps(result)[:8192] to SQLite. For sufficiently large results, this truncates inside a JSON token and makes result_json unparsable, even though the newly linked event digest still matches the damaged bytes. Option A: preserve a JSON prefix or raw preview, risking invalid encoding and ambiguous partial evidence. Option B (selected): store a small, valid JSON envelope with the original serialized UTF-8 byte count and SHA-256, marking the omitted payload explicitly. Neither option creates a new memory backend. Falsifier: any oversized stored result fails json.loads, the digest mismatches after restart, or a small result changes representation.

Changed bean/runtime/goal_cycle.py and bean/tests/test_goal_cycle.py on an isolated branch. A full result exceeding 8192 UTF-8 bytes is now stored as schema bean.goal.result_truncated.v1 with truncated=true, original_utf8_bytes and original_sha256. The compact event receipt has result_truncated and continues hashing exact persisted JSON. Existing small outputs remain unchanged. New regressions use non-ASCII data, restart, no replay, exact digest, and small-output compatibility. This is evidence-integrity engineering, not new learning or a complete cognition cycle.

## Current continuity and unknowns

Generation 50: 50 boots, 1672 events, Core archive SHA-256 a062af107d4d41f63b86b280e9b788dd72351209246b105e26e00dcedff40b7c; reasoning archive SHA-256 190df0178edee68318f99a5d492db48be3907e5ff7ce6d3b9729eceb773c06ba; receipt c50540e6d773d2abe019edd4e342e5effe7aa30bc2e42264c9c0c11ed5302c44; prior receipt 2a65419a6bad69ca61b079f3a3e566f55ba404e4e72b4af881bf33487a980399. Candidate, grammar-matched and passive all 144/144. Source SHA edbee2bcf0ebff97ed757bf36a4048c316f722af. No strong-control learning gain. PR #373 head 3fdb50b has 15 successful Actions workflows; these do not certify this branch.

HOURLY COGNITIVE SIMULATION NOT RUN: no fresh integrated Core learning experiment was dispatched or observed. Local git checkout failed DNS resolution for github.com. Exact-head CI for this branch is pending. Next: verify focused and full Core tests at exact head, inspect privacy/diff, merge only if green and reviewed, then register a bounded existing digital experiment with the default GoalCycle and demonstrate restart adaptation with paired controls.
