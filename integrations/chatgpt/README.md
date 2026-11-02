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

## Experimental direct-memory bridge: one-time connection, no copy/paste

**Status:** isolated research branch, not a hosted/approved public connector. BEAN's four default MCP tools remain read-only/stateless. A **separately opt-in** localhost-only extension registers:

| Tool | Actual action |
| --- | --- |
| `bean_remember_local(topic, note)` | Explicitly store a caller-supplied, UNVERIFIED note as a canonical event in BEAN Core's own SQLite database and reconciled JSONL audit mirror. |
| `bean_recall_local(query, limit=10)` | Search the most recent 48 hours of notes, return exact attributed matches, disclose differing statements and abstain on no match. |
| `bean_local_memory_status()` | Report durable BEAN session count, active-note count, retrieval window and limits. |

These tools let a **properly connected, authorized MCP client** send or retrieve notes in a normal conversation without copying/pasting text. They do not read a GitHub Pages tab's localStorage and do not magically connect ChatGPT to an open port. The 48-hour window affects *retrieval*, **not deletion**: the single-user SQLite file remains on disk until the local operator deletes its DB, WAL files and event mirror. The default off state is intentional.

### Local-only PowerShell setup for development

```powershell
cd D:\BEAN\core
python -m pip install psutil "mcp>=2,<3"
$env:BEAN_LOCAL_MEMORY_ENABLED="1"
$env:BEAN_LOCAL_MEMORY_DB="$env:USERPROFILE\.bean\mcp-memory.sqlite3"
$env:BEAN_MCP_HOST="127.0.0.1"
$env:BEAN_MCP_PORT="8000"
python -m integrations.chatgpt.server
```

The running service is locally reachable at `http://127.0.0.1:8000/mcp` by a suitable MCP inspector or client. Leave localhost-only; starting the memory-enabled server with a public bind is blocked in code. The extra tools are **not** turned on by the default server install.

For ChatGPT, **do not expect automatic port discovery or a website-triggered connection**. If your plan/workspace permits custom MCP apps, an authorized user must add and approve BEAN as a custom MCP server once. OpenAI documents [custom MCP server setup](https://developers.openai.com/api/docs/guides/custom-mcp-server) and the [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) for private/localhost services. Availability and write-tool permissions depend on the plan and workspace; installing or configuring any connection requires the user's explicit action. GitHub Actions are short-lived batch runners, **not persistent chat endpoints**.

**Single-user only, by design:** this local DB has no visitor identity isolation, server authentication or safe anonymous write-sharing. Never expose the memory tools as a public no-login endpoint or claim cross-user isolation. Don't store credentials, medical or private account information. Call `bean_remember_local` only after the user expressly asks to save a note; recalled notes are not independently verified facts. The Core process-wide singleton is serialized using the same lock as the four default MCP evidence tools.

The existing `docs/try-bean.html` is an independently labeled browser-local simulation. Direct MCP calls cannot read that page's browser storage; a trustworthy public real-memory service would require a separate privacy-reviewed hosted design.

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

## Axiom Favorites and navigation actions (separate local connector)

BEAN now has a **distinct local-only MCP navigation service** for the real
Axiom_Beta Favorites feature, under
`integrations/chatgpt/axiom_server.py`. It is **not** part of the existing
anonymous public read-only evidence demo above.

The service has four purpose-specific tools:

| MCP action | What it really does |
| --- | --- |
| `bean_find_axiom_pages(query)` | Searches Axiom's actual registered workspace destinations and returns local paths |
| `bean_list_axiom_favorites()` | Reads saved entries from the real Axiom SQLite database via its HTTP API |
| `bean_pin_axiom_favorite(module_key)` | Saves an existing registered workspace; confirms `saved=true` only after Axiom responds |
| `bean_remove_axiom_favorite(module_key)` | Unpins an existing workspace, reporting whether it was found |

Example: if the user asks "Pin Quality Forge in my favorites", the
connector looks up the real `quality` module key, calls the Axiom write API,
and says it was saved **only after** the response confirms it.
"I'll add that to your Favorites menu" alone is not a completion receipt.
BEAN remains responsible for deciding what to recommend; ChatGPT is the
natural-language interface.

Run **Axiom_Beta with its favorites branch installed** on the same PC; by
default it binds to `http://127.0.0.1:5060`. Then:

~~~sh
python -m pip install "mcp>=2,<3"
python -m integrations.chatgpt.axiom_server
~~~

The independent MCP service binds at `127.0.0.1:8001/mcp`. Axiom and the
connector stay on localhost, make no LLM calls, and use only registered suite
module keys. This is a **working local development contract**, not a
published ChatGPT app or an internet-accessible navigation service.
A remote ChatGPT session cannot directly connect to the user's localhost.
Supporting phones and remote sessions requires authenticated hosting/gateway
and per-user account routing, rather than blindly exposing this write-capable
service to the internet.

The tool result returns each item's `href` as a relative **Axiom path**.
Do not invent a public link from it. When a device has a reachable authenticated
Axiom host, its UI can make those paths clickable. The Axiom app itself
shows persistent Favorites in the left navigation and offers pin/unpin controls.

Tests:

~~~sh
python -m unittest bean.tests.test_axiom_navigation_chatgpt -v
python -m integrations.chatgpt.axiom_smoke
~~~

The `bean-axiom-navigation.yml` GitHub workflow additionally checks out
the actual Axiom source at a pinned commit and exercises the real Flask
database and HTTP endpoints on both Windows and Linux. These results prove
local integration only; no real-user authentication or ChatGPT deployment
has been established.
