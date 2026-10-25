---
name: software-audit
description: Evidence-first, read-only source design-conformity audit with independent BEAN Bridge integrity checks.
---

# BEAN Software Audit

Use pinned source checkouts and an explicit user- or maintainer-approved design manifest. Run \`python -m bean.integration.software_audit\` on the candidate files, retaining the JSON receipt. Never turn source presence, synthetic tests, or a successful boot menu screenshot into a functioning OS certification. For independent integrity review, use the Bridge checker \`scripts/bridge_software_audit_verify.py\` with the original candidate checkout. It must validate the receipt and ledger replay; show every failure and every unverified live gate. **Do not merge, release, auto-install BEAN, or mutate project source as part of an audit.** BEAN's original mascot/identity should be preserved; this skill makes no changes to UI or branding.
