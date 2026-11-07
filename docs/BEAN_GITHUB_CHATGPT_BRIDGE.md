# BEAN Core to ChatGPT via GitHub Issues

Status: public-only on-demand bridge. GitHub Actions is not a continuously
running inference server, and a GitHub issue is public. The bridge is for
owner-authored synthetic/public-safe experiments only.

## Design

1. ChatGPT, using the connected GitHub app as the repository owner, creates an
   issue titled with the exact prefix [BEAN] and a JSON request body.
   Alternatively, the owner can post a new JSON comment on an existing
   owner-created [BEAN] issue. The owner must be the GitHub sender.
2. GitHub Actions runs BEAN - ChatGPT GitHub request bridge. It validates the
   sender, issue origin, exact schema, field length and command allowlist.
   Existing reply markers block simple repeats after successful replies.
3. scripts/invoke_bean.py restores the two synthetic-only SQLite checkpoints
   under research/github_brain/, boots actual bean_run.py with disabled
   effectors and no configured model, verifies continuity, and uses the
   existing NativeReasoningService against that same reasoning database.
   It checkpoints both SQLite stores after native reasoning finishes.
4. GitHub Actions commits the recovered continuation to main and posts
   the actual result to the public issue, tagged BEAN_REPLY:....
5. ChatGPT can read the issue comments through the GitHub connector and relay
   the actual Core output or abstention. The source revision and receipt hash
   accompany the answer.

A GitHub Actions runner starts on demand and can be delayed. It is not
interactive always-on Python, nor a WebSocket service. The existing hosted
BEAN notes connector is a separate JavaScript adapter and does not silently
point at the local Jetson or the GitHub Core. A low-latency live ChatGPT tool
would require a persistent authenticated Core backend, not GitHub Pages alone.

## Example request

Create a new GitHub issue titled [BEAN] reasoning status, with body:

    {"schema":"bean.github.request.v1","command":"reasoning_status","args":{}}

A public synthetic symbolic reasoning attempt:

    {"schema":"bean.github.request.v1","command":"reasoning_local","args":{"domain":"public-demo","task_ref":"case-001","query":"What can you infer from prior demonstrations?"}}

A source-linked native lessons lookup:

    {"schema":"bean.github.request.v1","command":"reasoning_recall","args":{"domain":"public-demo","query":"prior measured results","limit":3}}

Only those three commands are supported, with strict envelopes and bounded
fields. Arbitrary Core commands, unbounded inputs and effectors are rejected.
reasoning_local is BEAN's real symbolic inference, with no hosted LLM fallback
in GitHub Actions. A correct result may be an explicit abstention. This bridge
does not train models, change code autonomously or connect the private Jetson.

## ChatGPT usage

When the GitHub connector is available, create the owner-authored issue in
danieloculus0-bot/BEAN with the title and public JSON above. Inspect its
bean-chatgpt-bridge.yml workflow run; after success and checkpoint commit, read
the resulting issue comment. If there is no output, state that BEAN has not
answered. Follow up on the same issue by posting a new owner-authored JSON
command comment. GitHub bot-generated result comments do not trigger another
authorized invocation.

There is no automatic session mirroring from ChatGPT. Never post conversations,
personal memories, employer data, private records, credentials or secrets into
the public GitHub repository. A private authenticated API is required for that.

## Evidence, concurrency and rollback

- Python invocation: scripts/invoke_bean.py
- Public receipt: research/github_brain/manifest.json
- Scheduled Core: .github/workflows/invoke-bean.yml
- Request parser: scripts/bean_github_issue_bridge.py
- Request action: .github/workflows/bean-chatgpt-bridge.yml
- Unit tests: bean/tests/test_github_issue_bridge.py
- Browser demo: docs/bean-demo/index.html

The new workflow reuses the existing Core concurrency group. Conflicting
non-fast-forward writes must fail rather than overwrite memory. Replies are
only posted after a checkpoint push succeeds. Rollbacks must preserve the
original experimental history.

## Dictionary patching

The browser experiment compares full JSON state snapshots against one base
snapshot plus deterministic changes, then replays and checks exact equality.
It does not change native BEAN SQLite. Real patch-ledger adoption needs
crash-safe recovery, versioned schemas, bounded snapshots, original evidence,
digest verification and matched comparisons against compressed SQLite.

A valid checkpoint is not evidence of subjective consciousness or AGI.
