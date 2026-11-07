# Invoke BEAN on GitHub main

This is a real **BEAN Python Core invocation**, not a simulated chatbot webpage. The workflow starts BEAN's existing Python runtime in GitHub Actions and carries a dedicated synthetic-only Core checkpoint forward through versioned repository commits.

## Start

Open [Invoke BEAN workflow](https://github.com/danieloculus0-bot/BEAN/actions/workflows/invoke-bean.yml), choose **Run workflow**, select **main**, and run. Once merged, this also runs hourly on a GitHub schedule, which may be delayed. A runner executes the actual bean_run.py Core tick loop, initializes its native reasoning service, handles predeclared digital brain-maintenance and model-update commands, reflects, and shuts down cleanly.

## Digital GitHub memory

Every successful main invocation commits exactly three *runner-generated synthetic* files under research/github_brain/: manifest.json, bean_memory.sqlite3.gz, and bean_reasoning.sqlite3.gz.

The SQLite files contain the full public-safe artificial Core event/identity state and native reasoning journal. The manifest records source SHA, generation, prior receipt hash, boot count, event count and integrity digests. On the next invocation, the script checks the previous receipt and both compressed databases, restores them into the next ephemeral runner and verifies that the Core actually advances one boot while retaining prior events. Refuse corrupt or missing checkpoints rather than silently resetting BEAN.

GitHub serves as **delayed, durable developmental storage and communication**. The actual runner is not always on; it briefly resumes Core each time GitHub schedules or dispatches it. No user-provided chats, workplace data, passwords, API keys or private local databases are included. The real Jetson/PC memory remains separate and private. The workflow injects its GitHub write credential only after the unprivileged Core exits and persistence checks succeed.

## Limits and evidence

Actual BEAN startup, self-model/cognition handlers, Core reflection, digital commands and restart persistence must be demonstrated by the workflow's integration job. The default run deliberately has no paid inference, local language-model server, new neural training, real-world motor action, external learning rewards, AGI or consciousness claims. Later measured digital tasks can be connected to the existing Core, not a second brain.

## Test

With Python and pytest from the repository root:

    python -m pytest bean/tests/test_github_invoke.py -q
    python scripts/invoke_bean.py --state-dir /tmp/bean-public-state --runtime-dir /tmp/bean-runner --ticks 12
    python scripts/invoke_bean.py --state-dir /tmp/bean-public-state --runtime-dir /tmp/bean-runner --ticks 12

The second command must report generation 2, two boots, a verified previous receipt, and more events than the first. GitHub PR CI performs those two real Core boots on an isolated runner before a merge.

For GitHub persistence, the repository's Actions permissions and main branch policy must allow the workflow's normal contents write. No force-push or automatic overwrite of a conflicting state is attempted.
