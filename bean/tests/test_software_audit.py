"""Software-audit skill: adversarial read-only and evidence-boundary regressions."""
import hashlib
import json
from pathlib import Path
import pytest
from bean.integration.software_audit import SCHEMA, audit_software

def manifest(*rules):
    return {"schema": SCHEMA, "project": "trial", "baseline_ref": "pinned-original",
            "candidate_ref": "pinned-candidate", "checks": list(rules)}

def rule(kind, path="hello.txt", **extras):
    return {"id": kind, "kind": kind, "path": path,
            "requirement": "test original design", "source_ref": "docs/design.md", **extras}

def test_real_bytes_and_no_implicit_runtime_proof(tmp_path):
    (tmp_path/"hello.txt").write_text("venvWin charcoal orange")
    result=audit_software(tmp_path,manifest(rule("contains_all",tokens=["venvWin","orange"]),
                                              rule("runtime_gate",path=None)))
    assert result["counts"] == {"pass":1,"fail":0,"unverified":1}
    assert result["verdict"]=="INCOMPLETE"
    assert result["live_guest_behavior_proven"] is False
    assert result["product_release_authorized"] is False
    assert len(result["receipt_sha256"])==64
    assert result["findings"][0]["evidence"][0]["sha256"] == hashlib.sha256(
        (tmp_path/"hello.txt").read_bytes()).hexdigest()

def test_forbid_real_regression_and_no_fake_green(tmp_path):
    (tmp_path/"hello.txt").write_text("BEAN_AUTOSTART=1")
    r=audit_software(tmp_path,manifest(rule("forbids_all",tokens=["BEAN_AUTOSTART"])))
    assert r["verdict"]=="FAIL"
    assert r["findings"][0]["status"]=="fail"

def test_baseline_byte_identity_requires_reference_checkout(tmp_path):
    (tmp_path/"hello.txt").write_bytes(b"hello")
    r=audit_software(tmp_path,manifest(rule("same_bytes",reference_path="design/source.txt")))
    assert r["verdict"]=="INCOMPLETE"
    baseline=tmp_path/"baseline"
    (baseline/"design").mkdir(parents=True)
    (baseline/"design/source.txt").write_bytes(b"hello")
    r=audit_software(tmp_path,manifest(rule("same_bytes",reference_path="design/source.txt")),reference_root=baseline)
    assert r["verdict"]=="STATIC_SOURCE_PASS"
    (baseline/"design/source.txt").write_bytes(b"altered")
    assert audit_software(tmp_path,manifest(rule("same_bytes",reference_path="design/source.txt")),reference_root=baseline)["verdict"]=="FAIL"

def test_git_object_identity_check_is_exact(tmp_path):
    content=b"approved-bean-mascot"
    (tmp_path/"hello.txt").write_bytes(content)
    expected=hashlib.sha1(b"blob "+str(len(content)).encode()+b"\x00"+content).hexdigest()
    assert audit_software(tmp_path,manifest(rule("git_blob",expected_blob=expected)))["verdict"]=="STATIC_SOURCE_PASS"
    assert audit_software(tmp_path,manifest(rule("git_blob",expected_blob="0"*40)))["verdict"]=="FAIL"

def test_missing_files_are_failures(tmp_path):
    assert audit_software(tmp_path,manifest(rule("present")))["verdict"]=="FAIL"

def test_rule_paths_cannot_escape_root(tmp_path):
    for outside in ["../secret.txt","/etc/passwd","bad\\path"]:
        r=audit_software(tmp_path,manifest(rule("present",path=outside)))
        assert r["verdict"]=="FAIL"
    (tmp_path/"escape").symlink_to("/etc/passwd")
    assert audit_software(tmp_path,manifest(rule("present",path="escape")))["verdict"]=="FAIL"

def test_duplicate_rule_ids_rejected(tmp_path):
    with pytest.raises(ValueError,match="duplicate"):
        audit_software(tmp_path,manifest(rule("present"),rule("present")))

def test_missing_independent_baseline_cannot_pass(tmp_path):
    (tmp_path/"hello.txt").write_bytes(b"anything")
    r=audit_software(tmp_path,manifest(rule("same_bytes",reference_path="not-here")))
    assert r["findings"][0]["detail"]=="reference_checkout_not_supplied"

def test_receipt_is_deterministic_and_non_credentialed(tmp_path):
    (tmp_path/"hello.txt").write_text("abc")
    m=manifest(rule("present"))
    r1=audit_software(tmp_path,m)
    r2=audit_software(tmp_path,m)
    assert r1==r2
    assert r1["source_authentication"]=="caller_supplied_checkout_not_independently_authenticated"
    assert r1["executed_project_code"] is False
