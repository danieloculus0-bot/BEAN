"""BEAN reads EZ-FEA's native torsion evidence and independently checks mechanics.

Input is a host-provided exported solver report; it has NOT authenticated
the producing GitHub Action or reproduced the CAD/mesh/solver execution.
No material strength, code approval or training reward is inferred.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re

SCHEMA = "bean.native_fea_evidence_review.v1"


def _real(x, name, *, positive=False):
    if type(x) not in (int, float) or not math.isfinite(x) or (positive and x <= 0):
        raise ValueError(f"{name} must be a finite " + ("positive" if positive else "number"))
    return float(x)


def _near(a, b, *, rel=1e-6, abs_tol=1e-10):
    return abs(a-b) <= max(abs_tol, rel*max(abs(a),abs(b)))


def crosscheck_native_torsion(report, *, source_ref=None):
    """Generate an internally checked, conservatively scoped rule observation."""
    if not isinstance(report, dict) or report.get("schema")!="ezfea.native_circular_torsion.v1":
        raise ValueError("Unsupported/absent native EZ-FEA torsion schema")
    if report.get("status")!="pass" or report.get("engineering_validation")!="not_established":
        raise ValueError("Native solver report is failed, incomplete or misrepresents validation")
    digest=report.get("source_step_sha256")
    if not isinstance(digest,str) or re.fullmatch(r"[0-9a-f]{64}",digest) is None:
        raise ValueError("Native CAD STEP SHA256 required")
    if source_ref is not None and (not isinstance(source_ref,str) or
                                    not 1 <= len(source_ref) <= 250):
        raise ValueError("Source link must be a bounded reference")

    geom=report.get("geometry")
    material=report.get("material")
    if not isinstance(geom,dict) or not isinstance(material,dict):
        raise ValueError("Explicit measured specimen and material details are required")
    radius=_real(geom.get("radius_mm"),"radius_mm",positive=True)
    length=_real(geom.get("length_mm"),"length_mm",positive=True)
    youngs=_real(material.get("youngs_mpa"),"youngs_mpa",positive=True)
    poisson=_real(material.get("poisson"),"poisson")
    if not -1.0 < poisson < .5:
        raise ValueError("Poisson ratio outside isotropic elastic domain")
    if report.get("element_type")!="C3D10":
        raise ValueError("Reference requires native C3D10 evidence")
    torque=_real(report.get("torque_nmm"),"torque_nmm")
    if torque == 0:
        raise ValueError("Nonzero applied torque required")
    shear_modulus=youngs/(2*(1+poisson))
    j=math.pi*radius**4/2
    theta=torque*length/(shear_modulus*j)
    tau=torque*radius/j
    if not all(math.isfinite(x) for x in (shear_modulus,j,theta,tau)):
        raise ValueError("Independent reference overflow")
    claimed_theta=_real(report.get("reference_tip_twist_rad"),"reference_tip_twist_rad")
    claimed_tau=_real(report.get("reference_surface_shear_mpa"),"reference_surface_shear_mpa")
    if not _near(theta,claimed_theta,rel=1e-8) or not _near(tau,claimed_tau,rel=1e-8):
        raise ValueError("Native reported analytical references disagree with BEAN calculation")

    records=report.get("records")
    if not isinstance(records,list) or len(records)<2:
        raise ValueError("A multi-grid native experiment is required")
    previous_size=math.inf
    previous_elements=0
    normalized=[]
    for index,r in enumerate(records):
        if not isinstance(r,dict) or r.get("status")!="pass":
            raise ValueError(f"Mesh {index} failed source evidence checks")
        size=_real(r.get("mesh_size_mm"),f"mesh {index} size",positive=True)
        elements=r.get("elements")
        if type(elements) is not int or elements<=0:
            raise ValueError("Real positive element count required")
        if size>=previous_size or elements<=previous_elements:
            raise ValueError("Mesh sizes must decrease and element count increase")
        previous_size,previous_elements=size,elements
        actual_theta=_real(r.get("measured_tip_twist_rad"),f"mesh {index} twist")
        observed_angle_error=abs(actual_theta-theta)/abs(theta)
        stored_angle_error=_real(r.get("twist_relative_error"),f"mesh {index} twist error")
        if not _near(observed_angle_error,stored_angle_error,rel=1e-6):
            raise ValueError("Measured twist and reported error disagree")
        fixed_moment=r.get("native_support_moment_nmm")
        if not isinstance(fixed_moment,list) or len(fixed_moment)!=3:
            raise ValueError("Real support moment vector is required")
        mx=_real(fixed_moment[0],f"mesh {index} fixed reaction torque")
        reported_torque_error=_real(r.get("reaction_torque_relative_error"),
                                    f"mesh {index} torque error")
        observed_torque_error=abs(mx+torque)/abs(torque)
        if not _near(observed_torque_error,reported_torque_error,rel=1e-6):
            raise ValueError("Fixed support reaction torque disagrees with reported error")
        audit=r.get("applied_audit")
        if not isinstance(audit,dict):
            raise ValueError("Applied torque nodal-force audit missing")
        applied_moment=audit.get("applied_moment_nmm")
        applied_force=audit.get("applied_force_n")
        if not isinstance(applied_moment,list) or len(applied_moment)!=3:
            raise ValueError("Missing applied nodal moment audit")
        if not isinstance(applied_force,list) or len(applied_force)!=3:
            raise ValueError("Missing applied nodal force audit")
        applied=[_real(x,"applied moment") for x in applied_moment]
        force=[_real(x,"applied force") for x in applied_force]
        if abs(applied[0]-torque)/abs(torque)>.0001:
            raise ValueError("Applied surface torque does not match requested load")
        if math.hypot(*force) > abs(torque)/radius*.02:
            raise ValueError("Applied torque contains unexpected net force")
        if observed_angle_error >= .15 or observed_torque_error >= .02:
            raise ValueError("Native results exceed experimental verification envelope")
        normalized.append({
            "mesh_size_mm":size,
            "elements":elements,
            "tip_twist_rad":actual_theta,
            "twist_error_fraction":observed_angle_error,
            "support_torque_nmm":mx,
            "torque_equilibrium_error_fraction":observed_torque_error,
        })

    normalized.sort(key=lambda x: -x["mesh_size_mm"])
    canonical=json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False)
    receipt=hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "schema":SCHEMA,
        "scope":"solid_circular_shaft_isotropic_linear_elastic_pure_torsion",
        "observation":"reference_equations_and_report_internally_consistent",
        "source_step_sha256":digest,
        "source_report_sha256":receipt,
        "source_ref":source_ref,
        "provenance_status":"host_attested_not_independently_authenticated",
        "replayed_native_solver":False,
        "independently_recomputed_references":True,
        "reference_tip_twist_rad":theta,
        "reference_surface_tau_mpa":tau,
        "model_inputs":{"radius_mm":radius,"length_mm":length,
                        "torque_nmm":torque,"youngs_mpa":youngs,"poisson":poisson},
        "grids":normalized,
        "bounded_rule":{
            "given":"straight solid circular shaft; torque about shaft axis; homogeneous isotropic small strain",
            "twist":"T*L/(G*J) with G=E/(2*(1+nu)), J=pi*r^4/2",
            "maximum_nominal_shear":"abs(T)*r/J",
            "not_included":["connections","stress concentrations","safety factors",
                            "materials failure","noncircular torsion","local support effects"],
        },
        "design_approval":False,
        "learning_weights_updated":False,
        "native_engineering_validation":"not_established",
    }


def main():
    parser=argparse.ArgumentParser(description="Cross-check imported EZ-FEA native torsion evidence")
    parser.add_argument("report",help="Actual TORSION_EVIDENCE.json exported from EZ-FEA")
    parser.add_argument("--out",default=None)
    parser.add_argument("--source-ref",default=None)
    args=parser.parse_args()
    data=json.loads(Path(args.report).read_text(encoding="utf-8"))
    result=crosscheck_native_torsion(data,source_ref=args.source_ref)
    rendered=json.dumps(result,indent=2)+"\n"
    if args.out:
        Path(args.out).write_text(rendered,encoding="utf-8")
    print(rendered)


if __name__=="__main__":
    main()
