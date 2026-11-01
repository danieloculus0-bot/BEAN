# BEAN on Jetson: inspect first, then install

This is a packaging update of the existing BEAN Python runtime, **not a new BEAN brain**. Run against JetPack 6 on an ARM64 Jetson. Existing BEAN memory, model files and motion experiments are not replaced.

## One-command diagnostic (from your existing BEAN repository directory)

This downloads the diagnostic source from a review branch without checking that branch out, does not install packages or edit the current checkout, and runs a one-tick smoke with disposable SQLite storage.

~~~sh
git fetch origin feature/jetson-package-preflight-20261101 && git show FETCH_HEAD:scripts/jetson_runtime_audit.py | python3 - --smoke
~~~

The diagnostic reports architecture, Python interpreter and package presence, active service state, existing camera/serial device names, loopback inference-server response, statically registered inbox commands and periodic tick handlers, and actual one-tick Core startup/import outcomes.

**Do not mistake the module count for active integration.** Static registration, successful imports, and synthetic smoke tests do not prove that vision, audio, learning, or motion actually execute together. The isolated smoke disables model inference and hardware output and uses the example body registry.

It does not read or upload private memory contents or secrets. Review terminal output before sharing it outside your trusted workspace.

## Packaging after checking the results

The existing installer remains install/jetson_brain_install.sh. This branch makes its paths use the current clone and Linux login instead of requiring a dedicated /home/bean account. It renders an actual systemd unit, preserves an existing /etc/bean/bean.env, creates a persistent data directory outside the repository, and installs lightweight Python dependencies in .venv.

The installer neither starts the service nor installs models. Do not run it until the diagnostic has identified the current runtime state and you have checked which copy of BEAN is running.

When ready to test this branch in an isolated checkout:

~~~sh
git fetch origin feature/jetson-package-preflight-20261101
git worktree add ../BEAN-jetson-review FETCH_HEAD
cd ../BEAN-jetson-review
bash install/jetson_brain_install.sh
~~~

No automatic physical actuation: existing BEAN Core uses MotionSimulator and the real Arduino motion bridge remains in separate PR #204. The local llama.cpp inference provider still expects a separately launched server at http://127.0.0.1:8080 using model alias bean-local. Existing hardware-specific body calibration and voice/camera modules require separate confirmation on the installed Jetson.

## Verification labels

- **Source validation:** automated tests check rendering, shell syntax and inventory behavior.
- **Jetson runtime:** NOT VERIFIED until the target terminal audit runs.
- **Local model integration:** NOT VERIFIED until inference responds successfully and BEAN's native reasoning handler is exercised.
- **Real motor and manipulation control:** NOT VERIFIED; not activated by this package.
