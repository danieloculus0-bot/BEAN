# Deploy BEAN's bounded MCP preview for Perplexity

**Observed deployment (November 10, 2026):** The owner-approved Render
Blueprint provisioned the `bean-perplexity-mcp-y55q` free web service.
Render reported its initial deploy at commit `d25be9df5f9ec438860d595f3f74bb4fe4582b4c`
as **Live**. Perplexity has reported reaching a bearer-protected endpoint,
but authenticated `tools/list` and `tools/call` from Perplexity itself remain
**UNVERIFIED**. Source on this feature branch may be newer than the deployed
commit. This uses the existing BEAN Python MCP service, **not** the separate
ChatGPT BEAN cloud-note plugin.

## What it serves

The existing four read-only, public-safe tools from
[integrations/chatgpt/server.py](server.py):
`bean_audit_claim`, `bean_compare_evidence`, `bean_screen_proposal`,
and `bean_demo_restart`. The persistence tool tests a **disposable,
fictional** SQLite case. It does not access the user's retained BEAN memory,
GitHub Core continuity, personal notes or local Jetson. There are no memory
writes or integrations with company data. Do not submit nonpublic information.

## Current deployment and Perplexity connection

- **Service:** [bean-perplexity-mcp-y55q](https://dashboard.render.com/web/srv-dbpk4pmi0phs73ae0t2g) in the owner's confirmed Render workspace.
- **MCP URL:** `https://bean-perplexity-mcp-y55q.onrender.com/mcp` (Streamable HTTP).
- **Public health URL:** `https://bean-perplexity-mcp-y55q.onrender.com/health`. A health response confirms the gateway is reachable, not an authenticated MCP tool call.
- **Authentication:** Render Environment `BEAN_MCP_API_KEY`, saved only in the user's Perplexity credential vault.
- **For Perplexity's Header API Key credential form:** Header name `Authorization`; header value `Bearer <RENDER_SECRET>` with one space after `Bearer`. The angle-bracket text is a placeholder, never an example real token. The selected credential host is `bean-perplexity-mcp-y55q.onrender.com`.
- **Discovery:** Enable the custom connector in the intended Perplexity thread, then explicitly list the four available BEAN tools and call `bean_audit_claim` with a fictional test claim.
- **Permission:** Perplexity Enterprise administrators may need to permit a member-owned connector. The user has to select and authorize any actual workspace-wide publication separately.

### If setting up a fresh deployment

The owner already created and approved a Render Blueprint for this repo's
`render.yaml`, targeting `feature/perplexity-remote-mcp-20261110`; a second
Blueprint is not needed. If rehosting, review the Blueprint plan before
approval, provision a secret through the host, run the CI smoke tests,
deploy via HTTPS, and record the *actual* returned host and deployed commit.
Never assume a repository push went live before checking Render's deploy status.

### Verification

- CI: `python -m integrations.chatgpt.http_smoke` checks the original local MCP service.
- CI: `python -m integrations.chatgpt.perplexity_http_smoke` checks local authenticated Streamable HTTP, public health, 401 without bearer, tools/list and a fictional tool call.
- Live Render: check deployment state and exact deployed commit in the service dashboard; Render free instances can sleep.
- Perplexity: separately verify successful authenticated discovery and a real tool response. A 401 response proves the authorization gate is rejecting unauthenticated requests, **not** that the credential is working.
- **Do not put keys in tests, GitHub, issue comments, public logs, or Perplexity prompts.** Revoke/rotate in Render and update the credential vault if compromised.

The Render **free** plan may sleep while idle and time out Perplexity's first
connection. Choose an always-on plan if reliable interactive use is needed.
The API key protects a single shared deployment, not individual tenants.
Restrict the key to trusted users, rotate it if exposed, and do not describe
it as Enterprise SSO/OAuth or an approved company integration. Logging
privacy, organization permission and any enterprise security review remain
the deployment owner's responsibility.

## Local checks

```bash
python -m pip install pytest psutil "mcp>=2,<3" uvicorn
python -m pytest bean/tests/test_public_plugin.py bean/tests/test_perplexity_auth.py -q
python -m integrations.chatgpt.http_smoke
python -m integrations.chatgpt.perplexity_http_smoke
# Optional locally authenticated preview:
BEAN_MCP_API_KEY=replace-with-a-random-long-private-token \
  uvicorn integrations.chatgpt.perplexity_remote:app --host 127.0.0.1 --port 10000
```

**What this does not solve:** synchronizing the private ChatGPT @BEAN plugin's
durable cloud D1 notes with another host. That requires a supported,
authenticated export/API, tenant identity mapping, and an explicit privacy
design. Do not imply the public sample server has those capabilities.
