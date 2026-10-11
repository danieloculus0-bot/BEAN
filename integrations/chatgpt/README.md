# BEAN ChatGPT Plugin — alpha implementation

**Current status: source-ready developer preview, NOT a published or hosted ChatGPT plugin.**

BEAN has its first bounded MCP integration. It exposes real existing BEAN Core routines through four small **read-only, stateless-for-users** tools:

| MCP tool | What it does | Scope / limitation |
| --- | --- | --- |
| `bean_audit_claim` | Uses BEAN's existing `EpistemicGuard` to flag missing provenance, confidence, falsification routes and capability overclaims | A heuristic screen. Even `approved` never means factual truth |
| `bean_compare_evidence` | Uses the actual BEAN `EvidenceBridge` and `SourceClaim` types to record 1–12 submitted observations per **temporary** SQLite evidence round and show contradictory reported positions | Caller-supplied evidence remains **unverified** even when two labels agree; never authenticates sources or websites |
| `bean_screen_proposal` | Uses BEAN's existing reasoning proposal filters and returns flags requiring review | Narrow keyword heuristics, not a safety certification or authorization to execute |
| `bean_demo_restart` | Calls Core's existing `examples.restart_continuity` to reopen SQLite and check the event, proposal and review state survived across two sessions | Synthetic mock provider, local temporary DB, **not** remembered user data or trained-model learning |

The public integration does **not** connect to internal BEAN state or any real ERP, bank, robot, crypto wallet, browser, OpenAI API, API key, external website, user account or data store. These public tools cannot write back to the host. No arbitrary code execution or network retrieval is exposed. Each evidence/claim call creates and deletes a disposable local BEAN database; Core's process-level memory store is guarded with a lock to prevent cross-request DB reuse. The service itself requires deployment privacy controls before allowing real users to submit text.

## Run locally

Prerequisites: Python 3.11+ (for the MCP server), Git, and a suitable virtual environment. From the BEAN repo root:

```bash
python -m pip install psutil "mcp>=2,<3"
python -m integrations.chatgpt.server
```

Defaults: `http://127.0.0.1:8000/mcp`, streamable HTTP with stateless JSON responses. The bind address can be set with `BEAN_MCP_HOST` and `BEAN_MCP_PORT`. Leave it on loopback during development; set `BEAN_MCP_HOST=0.0.0.0` only when deploying behind an approved HTTPS gateway with appropriate access controls, rate limits and logging policy.

Use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to connect over Streamable HTTP to `http://127.0.0.1:8000/mcp`. Check initialization, the four tools, read-only/open-world annotations, successful example calls, size limits and rejection of attempts to supply a `verified` property. The plugin is **not yet available in ChatGPT** because it lacks a production HTTPS endpoint and submission approval.

## Example calls

**Evidence disagreement**

```json
{
  "question": "Does the fictional inspection pass?",
  "observations": [
    {"origin": "report alpha", "statement": "pass"},
    {"origin": "report beta", "statement": "fail"}
  ]
}
```

Result: both reported positions are surfaced, `reported_positions_conflict=true`, `verified_independent_origins=0`, and `conclusion=null`. No provider is contacted.

**Missing source**

`bean_audit_claim(claim="A fictional machine meets tolerance")` returns a downgraded heuristic result and flags missing source, confidence and falsification path.

**Review a proposed action**

`bean_screen_proposal(summary="Examine reports", steps=["Review synthetic evidence"])` reports basic filters and explicitly requires human review; it performs no action.

**Prove Core persistence**

`bean_demo_restart()` uses the existing two-session test and confirms that a stored fictional event and pending-review proposal survived closing and reopening one disposable SQLite database.

## Package for ChatGPT and Codex

The draft portable package is in [`plugin/`](plugin/): `plugin.json` plus the `skills/evidence-first/SKILL.md` workflow. The `mcp.example.json` template must be copied to `mcp.json` **only after** BEAN has a real, stable, publicly reachable HTTPS `/mcp` endpoint. Replace the example URL with the actual endpoint. Never submit the `.example` endpoint to review or claim it works.

The optional plugin skill adds helpful guidance but does not provide a live MCP server by itself. Do not mark a skills-only install as server-backed. The future package will need approved icon assets, a final privacy/terms URL, correct company/developer display name, actual remote host, and valid review materials.

## What blocks public listing

1. **Hosting**: select and maintain a stable HTTPS server (not a GitHub Pages static site or short-lived localhost tunnel), with runtime safeguards, bounded request size, TLS, operational availability, source code revision, privacy policy and abuse/rate limiting. This code is not yet deployed anywhere.
2. **Safety/privacy**: review all network and platform access logs; protect posted user data, define retention and data deletion terms, verify no secrets or private files leak, and perform threat testing. **No long-term user memory, OAuth, private account connections or write actions** are enabled in this release.
3. **Publisher verification**: verify the individual or business name in the OpenAI Platform dashboard and ensure `api.apps.write` permissions before submitting.
4. **Review submission**: connect/test the real HTTPS endpoint with ChatGPT, prepare required positive/negative examples, upload a correctly configured plugin ZIP, complete the review form, await approval, then publish. Review does not automatically grant featured directory placement.

Official references: [Build an MCP server](https://developers.openai.com/plugins/build/mcp-server), [Package a plugin](https://developers.openai.com/plugins/build/plugins), [Submit a plugin](https://developers.openai.com/plugins/deploy/submission), [Remote MCP review requirements](https://developers.openai.com/plugins/deploy/app-review).

## Test and acceptance

```bash
python -m pip install pytest psutil
python -m pytest bean/tests/test_public_plugin.py -q
```

The separate plugin CI job installs `mcp>=2,<3` on Python 3.12 and checks SDK tool registration and read-only annotations. Core's full Windows/Linux Python 3.10/3.12 matrix runs the new public backend tests without requiring MCP (an optional dependency).

The first major **future** feature after proper per-user authentication and secure tenant storage is individual user continuity. That must never be implemented by sharing Core's global SQLite singleton or a public anonymous shared memory database across users.

**Public preview is not the same as a published ChatGPT integration.** BEAN remains publicly viewable source; repository visibility does not grant a redistribution license.
