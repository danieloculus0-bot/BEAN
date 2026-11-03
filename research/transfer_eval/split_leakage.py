"""Fail-closed provenance leakage audit for prospective held-out transfer trials.

Checks declared metadata, not semantic independence or authentic receipts.
No new persistence backend or runtime hooks.
"""

def audit_split(training, heldout):
    """Check case, dependency-family, source and receipt overlap across splits.

    Required keys: case_id, family_id, source_sha, receipt_sha.
    source_sha identifies originating artifact, not code revision.
    """
    train, test = list(training), list(heldout)
    if not train or not test:
        raise ValueError("both splits require at least one record")
    keys = ("case_id", "family_id", "source_sha", "receipt_sha")
    def collect(rows):
        ids = {key: set() for key in keys}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("record must be a mapping")
            for key in keys:
                value = row.get(key)
                if not isinstance(value, str) or not value.strip() or value != value.strip():
                    raise ValueError("missing or invalid " + key)
                if value in ids[key] and key in ("case_id", "receipt_sha"):
                    raise ValueError("duplicate " + key + " within split")
                ids[key].add(value)
        return ids
    train_ids, test_ids = collect(train), collect(test)
    overlaps = {key: sorted(train_ids[key] & test_ids[key]) for key in keys}
    return {
        "training_cases": len(train),
        "heldout_cases": len(test),
        "overlaps": overlaps,
        "heldout_separated": not any(overlaps.values()),
        "claim": "metadata_audit_only_not_semantic_independence_proof",
    }
