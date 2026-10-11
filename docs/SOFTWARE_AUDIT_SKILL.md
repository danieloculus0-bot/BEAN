# BEAN Software Audit Skill (read-only)

Run a bounded, source-referenced **design-conformity and artifact-integrity audit** against a checked-out project. The inputs are explicit requirements, candidate files, and optionally an independently selected baseline checkout. Every static check carries a file digest and exact rule provenance. Any live boot, hardware behavior, model performance, persistence, or Windows-program execution remains **UNVERIFIED** until separate evidence proves it.

## Supported checks

- \`present\`: exact file exists
- \`contains_all\` and \`forbids_all\`: case-sensitive UTF-8 source checks
- \`same_bytes\`: compare the candidate with an explicitly supplied baseline copy
- \`git_blob\`: compare a file's Git SHA-1 object ID against an anchored source
- \`runtime_gate\`: explicitly N/A pending live evidence, never silently passing

No code execution, network access, credential discovery, arbitrary commands, model-driven edits, or unsupported confidence percentages. A pass of **static** rules is not a release certification. Always pin Git SHA refs in CI and authenticate checkouts in the host; this tool cannot do that itself.

Usage:

\`\`\`bash
python -m bean.integration.software_audit \
  --root /path/to/checked-out-project \
  --manifest /path/to/design-checks.json \
  --reference-root /path/to/original-checkout \
  --output software-audit.json
\`\`\`

Exit \`0\` means **STATIC_SOURCE_PASS** only; \`2\` means source checks failed; \`3\` means incomplete evidence, even if every executable source rule passed. Output includes \`receipt_sha256\` computed over the canonical report excluding the receipt itself.

The BEAN Bridge verifier at \`scripts/bridge_software_audit_verify.py\` uses **actual \`ezbean.store.Ledger\`** and typed \`Observation\` to ingest, validate and replay immutable check outcomes; it independently recomputes the receipt and all source-file hashes against a host-selected checkout. Bridge verifies receipt integrity and ledger replay, **not** ownership of Git refs or real runtime functionality.

The venvWin example manifest has an intentional incomplete verdict until real Puppy/Wine persistence and native EXE/MSI execution gates are demonstrated. BEAN itself remains a **manual, separate tool** for venvWin, not an installed OS service.
