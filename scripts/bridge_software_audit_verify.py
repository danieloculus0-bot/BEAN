#!/usr/bin/env python3
"""Independent BEAN Bridge receipt and source-integrity verifier.

Uses the real Bridge typed Observation and append-only Ledger for replay.
Does not execute audited software, fetch GitHub refs, or certify live behavior.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from ezbean.core import Observation
from ezbean.store import Ledger

SCHEMA="bean.software_audit.v1"
KINDS={"present","contains_all","forbids_all","same_bytes","git_blob","runtime_gate"}

def sha(data: bytes)->str:
    return hashlib.sha256(data).hexdigest()

def canonical(obj)->str:
    return json.dumps(obj,sort_keys=True,separators=(",",":"))

def read(root: Path,relative: str):
    if not isinstance(relative,str) or not relative or len(relative)>400:
        raise ValueError("Bad path")
    p=Path(relative)
    if p.is_absolute() or ".." in p.parts or "\\" in relative:
        raise ValueError("Unsafe path")
    base=root.resolve(strict=True)
    target=(base/p).resolve()
    if not target.is_relative_to(base) or not target.is_file() or target.stat().st_size>8_000_000:
        raise ValueError("Missing/unavailable target")
    return target.read_bytes()

def recompute(root: Path, baseline: Path | None,rule: dict)->str:
    kind=rule["kind"]
    if kind=="runtime_gate":return "unverified"
    try:
        content=read(root,rule["path"])
        if kind=="present":return "pass"
        if kind in ("contains_all","forbids_all"):
            txt=content.decode("utf-8")
            contains=[term in txt for term in rule["tokens"]]
            return "pass" if (all(contains) if kind=="contains_all" else not any(contains)) else "fail"
        if kind=="git_blob":
            digest=hashlib.sha1(b"blob "+str(len(content)).encode()+b"\x00"+content).hexdigest()
            return "pass" if digest==rule["expected_blob"] else "fail"
        if kind=="same_bytes":
            if baseline is None:return "unverified"
            try:other=read(baseline,rule["reference_path"])
            except (ValueError,OSError):return "unverified"
            return "pass" if content==other else "fail"
    except (ValueError,UnicodeDecodeError,OSError):
        return "fail"
    raise ValueError("Invalid audit rule kind")

def verify(report: dict,manifest: dict,root: Path,baseline: Path | None=None)->dict:
    if manifest.get("schema")!=SCHEMA or report.get("schema")!=SCHEMA:
        raise ValueError("Wrong schema")
    raw={k:v for k,v in report.items() if k!="receipt_sha256"}
    if sha(canonical(raw).encode())!=report.get("receipt_sha256"):
        raise ValueError("Receipt digest mismatch")
    if report.get("product_release_authorized") is not False or report.get("live_guest_behavior_proven") is not False or report.get("executed_project_code") is not False:
        raise ValueError("Forged runtime or release claim")
    rules=manifest.get("checks")
    found=report.get("findings")
    if not isinstance(rules,list) or not isinstance(found,list) or len(rules)!=len(found):
        raise ValueError("Rule count mismatch")
    ledger=Ledger(":memory:")
    states={"pass":0,"fail":0,"unverified":0}
    try:
        for idx,(rule,entry) in enumerate(zip(rules,found)):
            if rule.get("kind") not in KINDS or not rule.get("source_ref"):
                raise ValueError("Invalid rule")
            if (entry.get("id")!=rule.get("id") or entry.get("path")!=rule.get("path")
                or entry.get("kind")!=rule.get("kind") or entry.get("source_ref")!=rule.get("source_ref")
                or entry.get("requirement")!=rule.get("requirement")):
                raise ValueError("Rule identity or provenance changed")
            status=recompute(root,baseline,rule)
            if entry.get("status")!=status:
                raise ValueError("Observed check disagrees with report")
            evidence=entry.get("evidence",[])
            if not isinstance(evidence,list):raise ValueError("Invalid evidence list")
            if rule["kind"]=="runtime_gate":
                if status!="unverified" or evidence:raise ValueError("Fake live proof")
            else:
                try: data=read(root,rule["path"])
                except (OSError,ValueError):data=None
                if data is not None:
                    if not evidence or evidence[0].get("sha256")!=sha(data) or evidence[0].get("bytes")!=len(data):
                        raise ValueError("Source digest mismatch")
                elif evidence:
                    raise ValueError("Evidence for missing source file")
                if rule["kind"]=="same_bytes" and baseline is not None:
                    try: ref=read(baseline,rule["reference_path"])
                    except (OSError,ValueError):ref=None
                    if ref is not None:
                        if len(evidence)!=2 or evidence[1].get("sha256")!=sha(ref):
                            raise ValueError("Reference digest mismatch")
            states[status]+=1
            event=Observation("bean_software_audit",str(rule["id"]),"software_check",
                              str(rule["id"]),"2026-10-11T00:00:00Z",
                              {"status":status,"digest":sha(canonical(entry).encode()),
                               "source_ref":rule["source_ref"]})
            if not ledger.ingest(event):raise ValueError("Unexpected duplicate check")
        replay=ledger.replay()
        if len(replay)!=len(found) or any(replay[i].payload["status"]!=found[i]["status"] for i in range(len(replay))):
            raise ValueError("Bridge ledger replay mismatch")
        if states!=report.get("counts"):
            raise ValueError("Count forgery")
        expected="FAIL" if states["fail"] else "INCOMPLETE" if states["unverified"] else "STATIC_SOURCE_PASS"
        if report.get("verdict")!=expected:
            raise ValueError("Verdict forgery")
        return {"schema":"bean.bridge.software_audit_receipt.v1",
                "verification":"INTEGRITY_REPLAY_VERIFIED",
                "report_sha256":report["receipt_sha256"],"bridge_events":len(replay),
                "source_files_rechecked":len([x for x in rules if x["kind"]!="runtime_gate"]),
                "observed_status":expected,"counts":states,
                "independent_live_guest_proof":False,
                "git_ref_authenticated_by_this_tool":False,
                "product_release_authorized":False}
    finally:
        ledger.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    p.add_argument("--reference-root",type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    result=verify(json.loads(a.report.read_text()),json.loads(a.manifest.read_text()),a.root,a.reference_root)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
