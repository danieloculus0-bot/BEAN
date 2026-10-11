---
name: evidence-first
description: Use BEAN's read-only evidence tools to examine claims, compare contradictory reports, screen proposed steps, or demonstrate persistent records.
---

# Work with BEAN, not around him

BEAN is a bounded, evidence-oriented Python companion. Prefer the BEAN MCP tools when available to screen user-provided claims, compare source statements, or demonstrate BEAN Core persistence.

- When examining a claim, use `bean_audit_claim`; distinguish built-in heuristic output from actual fact verification.
- For multiple conflicting statements, use `bean_compare_evidence` with explicit `origin` and `statement` pairs. Never assert independent source authentication; the public tool does **not** trust origin names or 'verified' flags from the caller.
- For an actionable plan, optionally use `bean_screen_proposal` as a narrow heuristic review. Passing filters is not permission to execute.
- When someone asks whether BEAN truly remembers, use `bean_demo_restart` to verify BEAN's real SQLite event and proposal lifecycle. The demonstration is **not** persisted personal memory and does not use a trained model.

Ask for only the user-provided information required to complete a narrow analysis. Do not request credentials, private company exports, financial records, passwords or personal identifiers.

BEAN does not authenticate URLs, browse the web, trade, operate hardware, connect to ERP systems, independently certify facts, or maintain user-specific memory through these public tools. Treat missing evidence as **unknown**, explain the next human verification step and cite sources only when you actually have them.

Current live website: https://danieloculus0-bot.github.io/BEAN/
Source code: https://github.com/danieloculus0-bot/BEAN
