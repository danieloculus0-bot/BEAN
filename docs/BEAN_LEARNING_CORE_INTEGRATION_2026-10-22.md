# BEAN Local Learning Integration, October 22, 2026

Source branch: integrate/bean-learning-core-20261022.

This integration brings the existing tested BEAN SpongeTD, SpongeIntuition
controller, compressed Q memory, and Lab027 benchmark from experiment
commit db1932eaf5f5bc709b7f8be0942b8438a0def3ae into the Python Core.

The BEAN runtime can now initialize the actual Q learner and connect it to
its existing file-based command inbox. Set the BEAN_LEARNING_DB environment
variable to a writable SQLite filename outside the code repository. Set
BEAN_LEARNING_ACTIONS to a JSON array of supported action strings if needed;
the default is ["up","right","down","left"].

Without BEAN_LEARNING_DB the learning commands are not installed. Setting
the variable never starts a training job automatically. An application or
agent must report observations and meaningful outcome rewards.

Inbox command arguments:

learning_choose:
{"episode_id":"case-1","domain":"maze","state":{"x":0},"location_ref":"node-1","legal_actions":["up","left"]}

learning_feedback:
{"episode_id":"case-1","reward":2.0,"next_state":{"x":1},"done":false}

learning_status:
{}

learning_checkpoint:
{"baseline":1.0,"candidate":2.0,"samples":40,"evaluation_sha256":"<64 lowercase hex SHA256>"}

The last feedback in an episode uses done:true. Each feedback updates
the original SpongeTD table using the actual temporal-difference equation.
The service prevents an outcome being counted twice after one choice,
enforces domain-scoped states, and remembers 64 concurrent episodes at most.
Actions are selected from caller-declared legal actions; BEAN does not
execute the selected action itself. No trades, network effects or hardware
commands are performed.

SQLite checkpoint records use the preexisting score-before-write Q codec
and SHA-linked journal. Recent in-memory rewards are NOT durable until
a successful checkpoint; process termination before a checkpoint loses
them. A supplied evaluation digest is host-reported, not independent
verification. Maintain matched validation and held-out evidence outside
this service before asserting that a policy improved.

This is not connected to the hosted JavaScript BEAN plugin, BEAN Bridge,
AIscend, Axiom, or other app runtimes yet. They need real sensor/outcome
interfaces. It does not train an LLM or general neural system.

Test commands:

    python -m unittest bean.tests.test_learning_runtime bean.tests.test_intuition_maze -v
    python -m pytest bean/tests -q

The original Lab027 Windows/Ubuntu source CI is:
https://github.com/danieloculus0-bot/BEAN/actions/runs/39550106061

This branch's CI must independently pass before merging to main.
