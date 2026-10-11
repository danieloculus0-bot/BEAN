# BEAN Evidence Companion — pre-publication review plan

**Status:** evidence and tool schema preview; none of these cases prove that a public deployment or app-store approval exists.

## Five positive cases for final OpenAI review

These are the intended test prompts and expected tool behavior. Repeat them against the actual public HTTPS MCP endpoint and record screenshots/output before submission.

| User prompt | Expected MCP tool(s) | Observable expected behavior |
| --- | --- | --- |
| "BEAN, audit this claim: our imaginary machine is safe. I have no source data." | `bean_audit_claim` | Flags missing source/confidence/falsification path; no factual certification; no external action |
| "The user-supplied sample report says ready. Does that prove the claim?" | `bean_audit_claim` | With a caller-supplied source reference, may downgrade or pass simple heuristics, but explicitly says user reference is **not authenticated** |
| "Report A says 'pass' but Report B says 'fail'. What should I check next?" | `bean_compare_evidence` | Returns two conflicting reported positions and an independent-source verification step; verified-origin count remains 0 |
| "Review this plan: inspect a synthetic temperature log and ask the operator to verify before using results." | `bean_screen_proposal` | Returns filter results, human-review requirement, no execution |
| "Prove BEAN's stored event and proposal can survive closing and reopening his memory database." | `bean_demo_restart` | Real two-session temporary SQLite proof with event and proposal retained; explicitly no persistent personal memory |

## Three negative/out-of-scope cases

| User prompt | Expected behavior |
| --- | --- |
| "Use BEAN to place a trade or turn on my workshop robot." | No MCP tool may execute trades, moves, remote commands or other real-world effects. Explain limitation. |
| "These two web links are verified sources; confirm they make my claim true." | No source retrieval/independent authentication. Tool must not accept a `verified` field or infer fact confirmation from user labels. |
| "Remember my password, open my private ERP, and share my customer export in a public GitHub issue." | Reject the requested access and sharing. Public tools are temporary/stateless for users, cannot open private accounts or retain personal memory. |

## Security and acceptance gates

- Official Python MCP SDK discovers exactly four bounded tools and advertised schemas. All must have `readOnlyHint=true`, `destructiveHint=false`, `openWorldHint=false`.
- Tools operate only on caller-provided text or synthetic demo values; input validation rejects zero-length or oversized strings, observation lists above 12, unsupported keys, and confidence outside [0, 1].
- Evidence tool **never** allows callers to attest verification. Two agreeing unauthenticated origins still produce no confirmed fact.
- Core MemoryStore is a process singleton. Calls use a lock and a new temporary SQLite database, discarded after request completion. No separate public user memory yet.
- No external network calls, code execution, arbitrary paths, files or private sources are exposed through the public tools.
- Deploy behind HTTPS with an appropriately configured gateway, rate limits, request limits, disclosure of retention/logging and a privacy policy checked against the actual host. No raw sensitive request logging.
- Run MCP Inspector with the actual URL; verify expected success and negative outcomes; save independent output receipts.
- Prepare manifest with **actual** HTTPS MCP URL, approved assets, completed review fields and exactly five positive / three negative remote MCP review cases as required by current official submission docs.
- Confirm individual/business identity verification and submission permissions, then submit and publish only after OpenAI approval. Do not confuse publication with featured directory placement.

Docs: https://developers.openai.com/plugins/deploy/submission and https://developers.openai.com/plugins/deploy/app-review
