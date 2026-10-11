"""BEAN chooses mechanical geometry; an independent CAD tool judges it.

The free model selects parameters, not prewritten source fixes. Trusted
CadQuery renders selected dimensions in a separate credential-free job.
The model never sees the independent checker implementation or reference CAD.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
FIELDS = ("length_mm","width_mm","height_mm","axle_bore_d_mm","bolt_bore_d_mm")
RANGES = {
    "length_mm": (34.0, 42.0),
    "width_mm": (30.0, 34.0),
    "height_mm": (20.0, 27.0),
    "axle_bore_d_mm": (6.50, 7.10),
    "bolt_bore_d_mm": (4.15, 4.80),
}
REFERENCE = {"length_mm":38.0,"width_mm":30.0,"height_mm":24.0,
             "axle_bore_d_mm":6.65,"bolt_bore_d_mm":4.30}
TASK = (
    "BEAN, design your own compact removable 1/4-inch axle mount to be made "
    "from 3D-printed material. Choose five numerical parameters for a "
    "real CAD geometry export. The part is a centered XY rectangular body "
    "with a through axle on X at Y=0, Z=height/2, and two vertical through "
    "mounting holes fixed at XY(-12,-10) and XY(+12,+10) mm. The independent "
    "CAD exporter and judge will use your choices, not any model-written "
    "success claims. Minimize material volume without sacrificing the "
    "specified mating fit and nominal material around the holes. "
    "Allowed dimensions (mm): body length [34,42], width [30,34], "
    "height [20,27], through axle bore diameter [6.50,7.10], "
    "mounting bolt bore diameter [4.15,4.80]. All hole centers are fixed "
    "by the mating interface. Include a brief design reason. "
    "Return only JSON: {\"length_mm\":number,\"width_mm\":number,"
    "\"height_mm\":number,\"axle_bore_d_mm\":number,"
    "\"bolt_bore_d_mm\":number,\"rationale\":\"short reason\"}. "
    "Do not use a CAD source code example, claim you ran a test, or "
    "assume physical certification. This is a simulated engineering test."
)


def digest(data):
    return hashlib.sha256(data.encode("utf-8") if isinstance(data,str) else data).hexdigest()


def parse_model_json(reply):
    if not isinstance(reply,str) or not reply.strip() or len(reply)>12000:
        raise ValueError("model response missing or oversized")
    reply=reply.strip()
    fence=chr(96)*3
    if reply.startswith(fence):
        lines=reply.splitlines()
        if len(lines)<3 or lines[-1].strip()!=fence:
            raise ValueError("incomplete JSON fence")
        reply="\n".join(lines[1:-1]).strip()
    decoder=json.JSONDecoder()
    data=None
    for start,c in enumerate(reply):
        if c!="{":
            continue
        try:
            value,_=decoder.raw_decode(reply[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value,dict) and all(k in value for k in FIELDS):
            data=value
            break
    if data is None or set(data)!=set(FIELDS)|{"rationale"}:
        raise ValueError("missing or unexpected dimensions")
    result={}
    for field in FIELDS:
        value=data[field]
        if type(value) not in (int,float) or not RANGES[field][0]<=value<=RANGES[field][1]:
            raise ValueError("model-selected dimension outside declared bounds: "+field)
        result[field]=round(float(value),4)
    rationale=data["rationale"]
    if not isinstance(rationale,str) or not 5<=len(rationale.strip())<=300:
        raise ValueError("missing concise design rationale")
    if all(abs(result[k]-REFERENCE[k])<0.05 for k in FIELDS):
        raise ValueError("unchanged fixture dimensions are not a new design")
    return result,rationale.strip()


def model_request(key, feedback, previous, *, opener=urlopen):
    if not key:
        raise RuntimeError("OPENROUTER_KEY_NOT_CONFIGURED")
    prompt=TASK
    if feedback:
        prompt+=(
            "\nPREVIOUS SEPARATE MECHANICAL QA REJECTED YOUR DESIGN. "
            "Choose your own revised dimensions. This is only the "
            "observed failure category, not the hidden test: "
            +feedback[:190]
            +"\nPrevious parameter proposal (for diagnostic context): "
            +json.dumps(previous,sort_keys=True)
        )
    payload=json.dumps({
        "model":MODEL,"temperature":0.3,"max_tokens":500,"stream":False,
        "messages":[{"role":"user","content":prompt}]
    }).encode("utf-8")
    req=Request(ENDPOINT,data=payload,method="POST",headers={
        "Authorization":"Bearer "+key,
        "Content-Type":"application/json",
        "X-Title":"BEAN chooses first self-directed CAD design",
    })
    try:
        with opener(req,timeout=105) as resp:
            response=json.loads(resp.read(75000).decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError("MODEL_HTTP_"+str(exc.code)) from None
    except (URLError,TimeoutError,OSError,UnicodeError,ValueError):
        raise RuntimeError("MODEL_TRANSPORT_OR_FORMAT_ERROR") from None
    if not isinstance(response,dict) or not isinstance(response.get("choices"),list) or not response["choices"]:
        raise RuntimeError("MODEL_NO_CHOICES")
    msg=response["choices"][0].get("message")
    if not isinstance(msg,dict):
        raise RuntimeError("MODEL_NO_MESSAGE")
    return msg.get("content"),str(response.get("model","unknown"))[:100]


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")


def choose(*, out, key, feedback=None, previous=None, request=model_request):
    report={"schema":"bean.cad.author.v1","status":"no_candidate",
            "model_requested":MODEL,"attempts":[],"design_sha256":None}
    for attempt in range(2):
        record={"number":attempt+1}
        report["attempts"].append(record)
        try:
            raw,served=request(key,feedback,previous)
            record["model_served"]=served
            params,reason=parse_model_json(raw)
            proposal={"schema":"bean.cad.proposal.v1",
                      "design_parameters_mm":params,
                      "rationale":reason,"model_served":served}
            save(out/"proposal.json",proposal)
            report.update(status="model_proposed_unverified",
                          design_sha256=digest((out/"proposal.json").read_bytes()))
            record["status"]="proposed"
            break
        except ValueError as exc:
            record.update(status="invalid_model_proposal",reason=str(exc)[:130])
        except RuntimeError as exc:
            record.update(status="provider_failure",reason=str(exc)[:130])
            report["status"]="provider_failure"
            break
    save(out/"author_receipt.json",report)
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=Path("_cad"))
    p.add_argument("--feedback",type=Path)
    p.add_argument("--previous",type=Path)
    args=p.parse_args()
    failure=None
    previous=None
    if args.feedback:
        receipt=json.loads(args.feedback.read_text(encoding="utf-8"))
        failure=str(receipt.get("reason","CAD quality gate rejection"))[:190]
    if args.previous and args.previous.is_file():
        prev=json.loads(args.previous.read_text(encoding="utf-8"))
        previous=prev.get("design_parameters_mm")
    result=choose(out=args.out,key=os.getenv("OPENROUTER_API_KEY",""),
                  feedback=failure,previous=previous)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
