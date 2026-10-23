# Autonomous change acceptance (review-only)

BEAN's code-authoring experiments are permitted to generate trial patches,
but **none may automatically merge or push to protected main**.

1. Record the source commit, source SHA-256, immutable test-input SHA-256,
   objective and tool versions. Baseline must reproduce the reported defect;
   a passing baseline is not evidence of a successful repair.
2. Execute candidate code in a disposable workspace without credentials.
   The original checkout and tests remain unchanged.
3. Verify the patch in a separate test job with no inference credentials;
   run the withheld acceptance and full regression tests. A rejected or
   timed-out candidate must not enter the acceptance artifact directory.
4. Compare the proposed content SHA-256 with independent platform receipts.
   Archive the attempt journal, fail/pass verdicts and candidate digests;
   use run-scoped GitHub Actions artifacts as evidence. Journal chain hashes
   detect accidental edits but do **not** make a writable database immutable.
5. Only produce a **draft pull request** on an isolated branch after all
   required jobs succeed. A separate authorized human reviews the diff and
   protected-branch CI before merge. Do not equate an experimental source
   candidate with validated production code.
6. Rollback before merge: close the draft PR and delete the isolated branch.
   Rollback after a separately authorized merge: revert the merge commit,
   rerun protected-main CI and verify persisted data compatibility. BEAN must
   never self-revert or self-promote a failed verification.

Current scope: self-repair workflow plus Lab019 research branch. This policy
is not a claim that every autonomous workflow has been audited; inventory all
other mutation-capable workflows before allowing any autonomous deployment.
