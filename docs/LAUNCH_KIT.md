# Meet BEAN 🌱 — Public launch kit

> **Cute name. Serious reasoning.** BEAN is the **Behavior Enabled Avatar Node**: a Python architecture for persistent reasoning, inspectable evidence, uncertainty, and versioned revision. It is experimental, and its limits are documented.

**Website:** https://danieloculus0-bot.github.io/BEAN/  
**Source:** https://github.com/danieloculus0-bot/BEAN  
**Offline five-minute quickstart:** https://github.com/danieloculus0-bot/BEAN/blob/main/docs/GETTING_STARTED.md  
**BEAN AI Bridge (separate prototype):** https://github.com/danieloculus0-bot/BEAN-AI-Bridge-  
**Research evidence:** https://github.com/danieloculus0-bot/BEAN/blob/main/docs/experimental-research-index-2026-10.md  
**Open feedback and bugs:** https://github.com/danieloculus0-bot/BEAN/issues/new/choose

## The one-sentence story

**BEAN remembers not only an answer, but the evidence, uncertainty, and revision trail behind it.**

### What is actually available today

- SQLite-backed event, session, and context persistence.
- Evidence and uncertainty handling, with review-required proposals rather than unrestricted model actions.
- Offline quickstart using a **mock** reasoning provider.
- An optional, separate Bridge module for host-verified evidence revision and contradiction retention.
- Linux and Windows continuous regression testing, plus documented positive **and negative** experiments.
- A cute little bean mascot, courtesy of the GitHub Pages site. The mascot is the brand; the claims must always come from reproducible engineering.

### One careful competitive result

In an independently graded **two-task synthetic coding pilot**, BEAN and Aider **tied**: both solved 2/2 tasks and passed 16/16 hidden tests. The comparison is a pilot, **not proof of BEAN outperforming Aider or other agents**, and it did not independently audit exact provider-side routes or Aider's LLM call counts.

Evidence: https://github.com/danieloculus0-bot/BEAN/actions/runs/38110050070

A later performance-optimization study's verdict was **INCONCLUSIVE_OR_INCOMPLETE**; do not market that as a win.

Evidence: https://github.com/danieloculus0-bot/BEAN/actions/runs/38110686371

## Copy-ready launch posts

These are drafts for genuine project accounts and creator-controlled submissions. Edit to your own voice, and disclose your involvement rather than posing as an independent reviewer.

### Short post — Bluesky / X / Threads

> Meet BEAN 🌱 Cute name. Serious reasoning. A Python architecture that remembers events, keeps evidence traceable, preserves uncertainty, and makes AI proposals reviewable. There's a free offline quickstart and the experimental results (including failures) are public. Come try it: https://danieloculus0-bot.github.io/BEAN/

### Developer-focused — LinkedIn / dev.to

> I built BEAN (Behavior Enabled Avatar Node) because giving an AI more context isn't the same as letting it account for what it knows. BEAN uses persistent SQLite-backed events, uncertainty tracking, evidence lineage, and host-controlled proposals to make reasoning inspectable over time. The open-to-view repo includes an offline mock-provider quickstart, Windows/Linux CI, and research results that show both progress and limitations. A separate Bridge prototype experiments with versioned evidence revision. I'd love feedback from developers interested in agent reliability and memory architecture: https://github.com/danieloculus0-bot/BEAN

### Show HN — propose only after a newcomer verifies the quickstart and the owner chooses a reuse license

**Suggested title:** Show HN: BEAN – evidence-aware memory and persistent reasoning in Python

**Suggested body:**

> I built BEAN, an experimental persistent-reasoning framework that stores events and evidence, tracks uncertainty, and keeps model proposals separate from the authority to act.
>
> You can reproduce its core event/proposal flow locally with Python and SQLite using a mock reasoning provider; no API key required. It isn't claiming AGI or autonomous general intelligence. The research index also documents failures.
>
> Website: https://danieloculus0-bot.github.io/BEAN/  
> Code and runnable quickstart: https://github.com/danieloculus0-bot/BEAN  
>
> I would appreciate feedback on the evidence model, source-verification boundaries, and API ergonomics. Where would this architecture be useful, and what would you try to falsify?

Check the community's current submission guidance before posting. Do not post using automated votes, sockpuppets, or indiscriminate duplicates.

### 90-second narrated demo outline

1. **0–15s** — Meet the smiling green mascot and run the offline quickstart.
2. **15–35s** — Record an event in the BEAN Core SQLite ledger. Show the event/trace ID.
3. **35–55s** — Produce a proposal with the mock provider and show that the host has **not** executed it.
4. **55–75s** — Demonstrate an unsupported answer kept unresolved, using synthetic observations in the separate Bridge learning-loop test. Show source origin and versioned revision when evidence is corroborated.
5. **75–90s** — Restart, inspect the persisted state and show exact reproducibility command and source link.

**Do not splice together the Core and Bridge demonstrations to imply they are a single active unattended process.** Label each run, version and fixture.

## Outreach targets and sequence

1. **Repo readiness:** owner sets the About description, website, topic tags and a deliberate LICENSE file. A public repository without a license is not automatically reusable open-source software.
2. **First wave:** owner posts one authentic project announcement from one connected personal/project account; reply thoughtfully to technical questions.
3. **Developer feedback:** share with developers already interested in Python agents, SQLite persistence, observability, and reproducible testing. Ask for actual issue reports and independent quickstart attempts.
4. **Second wave:** record the flagship demo and share the source, exact command, hidden-evaluation boundaries, and independent results.
5. **Technical writeup:** publish a longer breakdown of why missing data is *N/A*, not zero, and why model assertions should not certify themselves.
6. **Weekly maintainer update:** what BEAN now does; what failed; what changed; one reproducible invitation for a real use case.

**Success measures, not vanity goals:** external quickstart completions, independently reproduced claims, genuinely useful issues/PRs, sustainable stars/forks/watchers, and visitors returning for the next experiment. No bought engagement or fabricated benchmarks.

## Repo owner must configure GitHub About

**Description (copy):** `BEAN 🌱 Persistent reasoning in Python: evidence-aware memory, uncertainty, traceable revisions, and reviewable AI proposals.`

**Website:** `https://danieloculus0-bot.github.io/BEAN/`

**Topics:** `ai-agents`, `python`, `sqlite`, `agent-memory`, `persistent-memory`, `explainable-ai`, `reasoning-engine`, `ai-research`

**License:** deliberately choose one; no default assumed. Confirm licensing of code and third-party material first.

## Publishing limitations

As of the initial launch setup, only GitHub repository publishing was connected. Outside social accounts must be connected by the owner before this assistant can submit posts. All public statements must reflect **current** CI and audited experiment results; a green discovery harness is not proof of a successful model repair.

