"""Regenerable BEAN spaceflight test receipt with exact source hashes.

Run from the repository root:
    python -m research.spaceflight.ci_receipt --output spaceflight_receipt.json

The receipt records deterministic analytic checks, not independently measured
NASA ephemerides or mission software qualification.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import unittest

FILES = (
    "bean/engineering/spaceflight.py",
    "bean/engineering/two_body.py",
    "bean/runtime/inbox_handlers.py",
    "bean/runtime/inbox.py",
    "bean/tests/test_spaceflight_reference.py",
    "bean/tests/test_two_body_propagation.py",
    "bean/tests/test_spaceflight_inbox.py",
    "research/spaceflight/ci_receipt.py",
    ".github/workflows/bean-spaceflight-reference.yml",
)
TEST_MODULES = (
    "bean.tests.test_spaceflight_reference",
    "bean.tests.test_two_body_propagation",
    "bean.tests.test_spaceflight_inbox",
)


def receipt():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(TEST_MODULES)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    source_hashes = {
        path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if Path(path).is_file() else None
        for path in FILES
    }
    payload = {
        "schema": "bean.spaceflight_verification_receipt.v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "github_sha": os.getenv("GITHUB_SHA"),
            "github_run_id": os.getenv("GITHUB_RUN_ID"),
            "github_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
            "github_job": os.getenv("GITHUB_JOB"),
        },
        "source_sha256": source_hashes,
        "evidence_class": "deterministic_analytic_regression_not_independent_ephemeris",
        "test_modules": list(TEST_MODULES),
        "tests_run": result.testsRun,
        "tests_passed": result.testsRun - len(result.failures) - len(result.errors)
                        - len(result.skipped) - len(result.expectedFailures)
                        - len(result.unexpectedSuccesses),
        "failures": [{"test": str(test), "traceback": tb} for test, tb in result.failures],
        "errors": [{"test": str(test), "traceback": tb} for test, tb in result.errors],
        "skipped": [{"test": str(test), "reason": why} for test, why in result.skipped],
        "expected_failures": [str(test) for test, _ in result.expectedFailures],
        "unexpected_successes": [str(test) for test in result.unexpectedSuccesses],
        "successful": result.wasSuccessful() and all(source_hashes.values()),
        "flight_qualified": False,
        "jpl_horizons_state_vectors_compared": False,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False)
    payload["receipt_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="spaceflight_receipt.json")
    args = parser.parse_args()
    data = receipt()
    Path(args.output).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")
    print(f"Spaceflight receipt: {data['tests_run']} tests, "
          f"{len(data['failures'])} failures, {len(data['errors'])} errors, "
          f"SHA256 {data['receipt_sha256']}")
    return 0 if data["successful"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
