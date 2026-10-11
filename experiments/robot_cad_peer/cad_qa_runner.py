"""Credential-free CAD exporter / verifier for BEAN-selected parameters.

Only trusted parametric CadQuery code from the independent Bridge lab is
executed. The model writes NUMERIC design choices, not executable Python.
All dimensions are checked again here; model-authored 'success' is ignored.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

from experiments.robot_cad_peer.bean_design_request import parse_model_json, digest, save

BRIDGE_SHA="8037a69fb3af74597eebde3daad14fe4d42b721c"


def check_revision(bridge):
    r=subprocess.run(["git","rev-parse","HEAD"],cwd=bridge,check=True,
                     capture_output=True,text=True,timeout=15)
    if r.stdout.strip()!=BRIDGE_SHA:
        raise ValueError("unapproved Bridge CAD QA revision")


def judge(proposal_path, author_receipt, bridge, out):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    result={"schema":"bean.cad.independent-verdict.v1","status":"REJECTED",
            "reason":"unknown","source_commit":BRIDGE_SHA,
            "model_design_sha256":None}
    try:
        check_revision(bridge)
        if not proposal_path.is_file() or proposal_path.is_symlink():
            raise ValueError("no model CAD proposal")
        if not author_receipt.is_file() or author_receipt.is_symlink():
            raise ValueError("no source author receipt")
        authored=json.loads(author_receipt.read_text(encoding="utf-8"))
        raw=json.loads(proposal_path.read_text(encoding="utf-8"))
        if authored.get("schema")!="bean.cad.author.v1" or authored.get("status")!="model_proposed_unverified":
            raise ValueError("model author status not verified")
        if authored.get("design_sha256")!=digest(proposal_path.read_bytes()):
            raise ValueError("model proposal SHA does not match author's receipt")
        if raw.get("schema")!="bean.cad.proposal.v1" or not isinstance(raw.get("design_parameters_mm"),dict):
            raise ValueError("invalid model proposal schema")
        if set(raw)!={"schema","design_parameters_mm","rationale","model_served"}:
            raise ValueError("unexpected extra proposal keys")
        params,rationale=parse_model_json(json.dumps({
            **raw["design_parameters_mm"],"rationale":raw["rationale"]
        }))
        if raw["model_served"] not in [attempt.get("model_served")
                                       for attempt in authored.get("attempts",[])
                                       if attempt.get("status")=="proposed"]:
            raise ValueError("model provenance mismatch")
        sys.path.insert(0,str((Path(bridge)/"experiments/robot_cad_peer").resolve()))
        from axle_fixture import AxleBlock, export_fixture, make_model
        from verify import validate
        base=AxleBlock()
        part=replace(base,**params)
        output=out/"cad"
        export_fixture(output,spec=part)
        quality=validate(output)
        base_volume=float(make_model(base).val().Volume())
        result.update(status="PASSED",reason="independent STEP/STL mechanical gate passed",
                      model_design_sha256=digest(proposal_path.read_bytes()),
                      parameters=params,rationale=rationale,
                      cad_qa_status=quality["status"],
                      measured_volume_mm3=quality["step_volume_mm3"],
                      baseline_volume_mm3=round(base_volume,3),
                      volume_vs_reference_percent=round(
                          (quality["step_volume_mm3"]/base_volume-1)*100,2),
                      cad_geometry_sha256=quality["sha256"],
                      note="BEAN selected dimensions; trusted CadQuery template generated geometry; not topology invention or proven hardware fit")
    except Exception as exc:
        result.update(status="REJECTED",
                      reason=(type(exc).__name__+": "+str(exc))[:200])
    finally:
        save(out/"qa.json",result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--proposal",type=Path,default=Path("_design/proposal.json"))
    p.add_argument("--author-receipt",type=Path,
                   default=Path("_design/author_receipt.json"))
    p.add_argument("--bridge",type=Path,default=Path("_bridge"))
    p.add_argument("--out",type=Path,default=Path("_qa"))
    args=p.parse_args()
    result=judge(args.proposal,args.author_receipt,args.bridge,args.out)
    print(json.dumps(result,sort_keys=True,indent=2))
    # In automated experiments a rejected design remains a factual receipt,
    # not a pretended pass; job output gates the optional second model round.
    return 0


if __name__=="__main__":
    raise SystemExit(main())
