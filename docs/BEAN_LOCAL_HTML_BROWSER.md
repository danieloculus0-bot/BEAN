# BEAN local HTML browser capability (experimental)

BEAN's existing Python Core now has an optional local browser tool surface.
It reuses Chromium via Playwright, rather than inventing another HTML engine.
This is not part of the public Render/ChatGPT MCP evidence service.

## Implementation

- bean/integration/html_browser.py: isolated Chromium contexts that can
  inspect original HTML and inline scripts with page JS disabled, or execute
  the real page in Chromium when explicitly requested.
- Returns bounded source and rendered DOM excerpts, SHA-256 identifiers,
  visible text, page title, script snippets and linked script references,
  console output, page errors, blocked requests and action receipts.
- Supports up to eight bounded click/fill actions per call.
- integrations/chatgpt/local_html_server.py: two Streamable HTTP MCP tools,
  bean_html_inspect and bean_html_run. Runs browser work in a worker thread
  rather than blocking the MCP event loop.

No model is claimed to have used these tools until the actual local connector
is installed, discovered and invoked by the user's authorized desktop client.

## Private workstation

From an authorized BEAN checkout install:

    python -m pip install playwright==1.55.0 "mcp>=2,<3"
    python -m playwright install chromium

Set BEAN_HTML_ROOT to a small authorized workspace containing the HTML and
its local script/CSS files. Example on Windows PowerShell:

    $env:BEAN_HTML_ROOT = 'C:\authorized\html'
    python -m integrations.chatgpt.local_html_server

The connector binds only to 127.0.0.1:8002/mcp by default. It is separate
from the BEAN public server and any other local Perplexity/Core connector.
A desktop client must be configured to discover this local endpoint.
Never publish the endpoint or expose its tools through the public Render
deployment.

By default no HTTP(S) origins are permitted. To authorize specific origins,
set BEAN_HTML_ALLOWED_ORIGINS to a comma-separated list of explicit origins,
for example http://127.0.0.1:8765. Do not allow untrusted sites or publish
private browser results. Navigation and resource requests to other origins
are blocked. Browser contexts use no saved login profile, shared cookies
or direct Python shell/file write API.

## Verification

    python -m unittest bean.tests.test_html_browser -v

The synthetic Chromium tests check disabled and enabled page JavaScript,
script visibility, actual linked-script evaluation, fill and click actions,
network request blocking, root confinement and MCP SDK tool invocation.
The exact-head Actions outcome is reported by the PR, not assumed here.

## Known boundaries

This is a bounded first browser tool, not a full agent browser or full
desktop UI. Persistent interactive sessions, file-picker automation,
download/save-back, screenshots, external account credentials, or arbitrary
user JavaScript evaluation are not exposed by these first two tools.
Scripts can be read and executed in an isolated browser; the calling model
must still reason about code and inspect outcomes.

EZ-Office Sheets already handles CSV and a limited first-sheet XLSX import,
but does not support old-format XLS. Use the existing BEAN-AI-Bridge legacy
BIFF adapter under review for that format, not another reader. Large paged
business reports require source reconciliation beyond visual rendering.
Do not commit or upload proprietary files, source excerpts or work data.

No BEAN local journal or checkpoint is automatically updated by a browser
call. Verified results can be retained using existing private BEAN memory,
with appropriate source attribution and explicit authorization. Browser
execution alone is not evidence of learning or general intelligence.
