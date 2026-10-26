"""One-time project profile entry for BEAN Jobsite by a responsible reviewer.

Only records supplied limits and their provenance; cannot verify authority.
Does not supply species/grade design values or adopt any building code.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from .jobsite import _number
from .jobsite_web import load_profile


def create_profile(name, limits_source, limits):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Project name required")
    if not isinstance(limits_source, str) or not limits_source.strip():
        raise ValueError("Documented source of material limits required")
    record = {"schema":"bean.jobsite_profile.v1","name":name.strip(),
              "limits_source":limits_source.strip(),"project_defaults":{}}
    for key in ("modulus_psi","allowable_bending_psi","allowable_shear_psi","deflection_limit_ratio"):
        record["project_defaults"][key]=_number(limits.get(key),key)
    if record["project_defaults"]["deflection_limit_ratio"] <= 1:
        raise ValueError("L/n deflection ratio denominator must be above one")
    return record


def main():
    parser=argparse.ArgumentParser(description="Set reviewed project screening limits once")
    parser.add_argument("--out",default="jobsite-project.json")
    args=parser.parse_args()
    print("BEAN Jobsite setup: enter values from a checked design source.")
    print("Do not enter guesses or generic '2x4' strengths.")
    name=input("Project / material profile name: ").strip()
    source=input("Approved engineering document/reference: ").strip()
    fields=(
      ("modulus_psi","Elastic modulus E (psi)"),
      ("allowable_bending_psi","Adjusted allowable bending stress (psi)"),
      ("allowable_shear_psi","Adjusted allowable shear stress (psi)"),
      ("deflection_limit_ratio","Deflection L / denominator"),
    )
    limits={key: float(input(label+": ").strip()) for key,label in fields}
    record=create_profile(name,source,limits)
    path=Path(args.out)
    if path.exists():
        raise FileExistsError(f"Profile already exists: {path}. Choose another filename.")
    path.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    load_profile(path)
    print(f"Saved limits to {path}. Have a qualified reviewer check them before use.")
    print(f"Run: python -m bean.engineering.jobsite_web --profile {path}")


if __name__=="__main__":
    main()
