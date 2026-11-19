# BEAN Core curiosity-driven skill acquisition

This increment connects BEAN's established Curiosity, GoalStateEngine, GoalCycle, NativeReasoningService and Lab019 Skill Incubator. Curiosity selects a skill ID, GoalCycle persists and executes it, the existing configured BEAN model writes code, and Lab019 tests frozen training and separate holdout suites. Successful source is archived in the existing SHA-chained SQLite experiment journal and not installed into Core automatically.

This is bounded native autonomous goal execution, not general intelligence, consciousness, general model learning or unconstrained independent skill creation. The host chooses catalog entries and evaluation fixtures first.

## Trusted local catalog

Save a JSON catalog in a private host directory such as local_curriculum/skills.json:

    {
      "schema": "bean.native_skill_catalog.v1",
      "skills": [
        {
          "skill_id": "double",
          "name": "double",
          "objective": "Implement a reusable doubling function for signed integers",
          "training_project": "training",
          "holdout_project": "holdout"
        }
      ]
    }

The training and holdout project paths are relative to the local catalog file. Each has an independent Python unittest suite under tests/. The project sources are copied into temporary directories before evaluation. Candidate source cannot see the holdout tests in the model prompt.

## Existing BEAN startup

Use the existing Jetson / desktop BEAN entry point with its already configured reasoning provider, and set these environment variables:

    BEAN_SKILL_CATALOG=/absolute/path/local_curriculum/skills.json
    BEAN_GOAL_CYCLE=1
    BEAN_REASONING_ENABLED=1

Optional BEAN_SKILL_JOURNAL and BEAN_SKILL_OUTPUT select output locations; otherwise, private Lab019 SQLite journal and candidate artifacts reside beside the Core database. No live owner data is written to GitHub by this code.

An existing curiosity question with this context becomes an executable persisted GoalCycle investigation:

    {
      "schema": "bean.cognition.skill_question.v1",
      "skill_id": "double"
    }

Only host catalog IDs are allowed. Model-generated goals cannot supply Python test code, filesystem paths or provider credentials. Non-skill native reasoning experiments continue through the pre-existing registered handler.

The registered Core model writes Python source, the Lab019 engine executes actual frozen tests in disposable project copies and archives candidate attempts. A separate held-out test suite must pass before skill_promotion_ready is true. A failed holdout stops this authoring objective; the hidden expected answers are not returned to the model. Missing model produces unverified, not a fabricated success. GoalCycle persists action outcome and never silently reruns interrupted work.

## Evidence and limitations

Cross-platform synthetic tests exercise actual GoalStateEngine, GoalCycle, provider response adapter, generated Python module, frozen training/holdout tests, SHA journal and restart non-replay. This does not establish real-model learning, actual generalization, live skill deployment, or advantage over BabyAGI. Main manifest generation 66 reports 144/144 candidate and 144/144 grammar-matched control, which is a tie against the strong control.

Next falsifiable steps: let BEAN expand the host-independent curriculum based on evidence, compare novel unseen skills under identical budgets, evaluate independent reuse after restart, prove real model performance and negative/ablation controls. Drawing and scientific exploration retain their separate existing experiment ledgers.

## BEAN CONTEXT ACK v1

Task: Connect genuine native curiosity goals to existing Core model and Lab019 new-skill generation.
Existing systems checked: AGENTS, AI_GATEKEEPER, bean_run.py, GoalStateEngine, GoalCycle, digital_experiment, NativeReasoningService, Skill Incubator and manifest generation 66.
Assets reused: Core reasoning model, SQLite goal receipt store, Lab019 model writer/evaluator, SHA journal and candidate recovery.
Ledger: consulted generation 66 summary; no independent replay of historical compressed data.
Current evidence: CI pending on this feature head, synthetic only.
Unknowns: real model/provider reachability and independent novel-skill generalization.
Minimum change: host-curated skill experiment adapter, new structured question, native boot registration, tests.
Runtime/policy change: skill acquisition becomes available when a trusted local catalog is configured. Normal reasoning and robot control remain unchanged.
