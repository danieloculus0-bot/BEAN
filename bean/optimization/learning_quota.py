"""BEAN 3,000-run research quota: one credit per independently verified self-fix.

A Q-learning trial and a bug repair are DIFFERENT evidence types. Credit a
repair against the quota only if BEAN proposed the patch, the patch fixed a
reproducible failed regression, and an independent verifier signed the receipt
using a secret BEAN cannot access.

This module merely audits attested receipts and computes quota. It cannot
verify GitHub Actions jobs by itself and does not patch programs.
"""
from __future__ import annotations

import hashlib
import hmac
import json

SCHEMA="bean.optimization.quota.v1"


def canonical(data):
    return json.dumps(data,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_digest(value,name):
    if not (isinstance(value,str) and len(value)==64 and all(
            char in "0123456789abcdef" for char in value)):
        raise ValueError(f"{name} must be a SHA-256 hex digest")
    return value


def unsigned_receipt(*, bug_id, task, patch_sha256,
                     failing_test_sha256, passing_test_sha256,
                     baseline_revision, fixed_revision,
                     proposed_by, fixed_by,
                     independent_evaluator, report_reference):
    """Record the independently observed regression, source change, rerun.

    Only a legitimate independent evaluator can sign the result. The mere
    existence of an unsigned receipt gives zero quota credit.
    """
    values=(bug_id,task,baseline_revision,fixed_revision,
            proposed_by,fixed_by,independent_evaluator,report_reference)
    if not all(isinstance(x,str) and 0<len(x)<=200 for x in values):
        raise ValueError("missing or oversized fix evidence")
    if proposed_by != "BEAN" or fixed_by != "BEAN":
        raise ValueError("external or assistant repairs cannot earn self-fix credits")
    if independent_evaluator=="BEAN":
        raise ValueError("self-evaluation is not independent")
    if baseline_revision==fixed_revision:
        raise ValueError("fix must change a revision")
    hashes=(strict_digest(patch_sha256,"patch_sha256"),
            strict_digest(failing_test_sha256,"failing_test_sha256"),
            strict_digest(passing_test_sha256,"passing_test_sha256"))
    if hashes[1]==hashes[2]:
        raise ValueError("passing and failing evaluations cannot be identical")
    return {"schema":SCHEMA,"bug_id":bug_id,"task":task,
            "patch_sha256":hashes[0],
            "failing_test_sha256":hashes[1],
            "passing_test_sha256":hashes[2],
            "baseline_revision":baseline_revision,
            "fixed_revision":fixed_revision,
            "proposed_by":proposed_by,"fixed_by":fixed_by,
            "independent_evaluator":independent_evaluator,
            "report_reference":report_reference}


def evaluator_sign(payload,key):
    """This runs ONLY in the independent evaluator, never BEAN's agent.

    Caller must independently confirm failed-test -> patch -> passing-test
    evidence before calling this signing helper.
    """
    if not isinstance(key,bytes) or len(key)<32:
        raise ValueError("external evaluator needs >=32 bytes secret key")
    if set(payload)!={"schema","bug_id","task","patch_sha256",
                     "failing_test_sha256","passing_test_sha256",
                     "baseline_revision","fixed_revision",
                     "proposed_by","fixed_by",
                     "independent_evaluator","report_reference"}:
        raise ValueError("unknown or missing evidence field")
    unsigned_receipt(**{k:v for k,v in payload.items() if k!="schema"})
    return {"claim":payload,"hmac_sha256":hmac.new(key,canonical(payload),
                                                  hashlib.sha256).hexdigest()}


def verify_evaluator(receipt,key):
    if not isinstance(receipt,dict) or set(receipt)!={"claim","hmac_sha256"}:
        raise ValueError("unsigned or malformed fix credit")
    unsigned=receipt["claim"]
    expected=evaluator_sign(unsigned,key)
    if not hmac.compare_digest(expected["hmac_sha256"],receipt["hmac_sha256"]):
        raise ValueError("independent signature mismatch")
    return unsigned


def quota(*, target=3000, q_episodes, repair_receipts=(), evaluator_key=None):
    """Calculate remaining events after measured Q trials + verified self-fixes.

    Each bug_id and patch is credited only once. Claimed fixes are never
    converted to fake Q updates. Existing extra Q events remain visible.
    """
    if type(target) is not int or not 1<=target<=100000:
        raise ValueError("invalid quota target")
    if type(q_episodes) is not int or q_episodes<0:
        raise ValueError("q_episodes must be a nonnegative measured count")
    if not isinstance(repair_receipts,(tuple,list)):
        raise ValueError("fix receipts must be a sequence")
    if repair_receipts and evaluator_key is None:
        raise ValueError("independently signed evidence and key required")
    fixed=[]
    bug_ids=set()
    patches=set()
    for item in repair_receipts:
        claim=verify_evaluator(item,evaluator_key)
        if claim["bug_id"] in bug_ids or claim["patch_sha256"] in patches:
            raise ValueError("duplicate bug credit or duplicate patch")
        bug_ids.add(claim["bug_id"])
        patches.add(claim["patch_sha256"])
        fixed.append({"bug_id":claim["bug_id"],
                      "patch_sha256":claim["patch_sha256"],
                      "evidence_sha256":digest(canonical(item)),
                      "external_evaluator":claim["independent_evaluator"]})
    earned=len(fixed)
    completed=min(target,q_episodes+earned)
    return {"schema":SCHEMA,"target":target,
            "actual_q_episodes":q_episodes,
            "independently_verified_BEAN_bug_fixes":earned,
            "credited_units":completed,
            "remaining":target-completed,
            "excess_learning_episodes":max(0,q_episodes+earned-target),
            "bug_fix_receipts":fixed,
            "claim":"credits_do_not_substitute_for_q_ledger_events"}
