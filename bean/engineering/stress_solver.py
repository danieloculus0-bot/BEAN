"""Independent closed-form mechanics reference, invoked through the BEAN inbox.

Scope: homogeneous, straight, solid circular shaft, linear elasticity,
Saint-Venant torsion, beam-theory bending and uniform axial force. This is
a genuine deterministic numerical calculation, not a trained FEA surrogate or
a stress field for arbitrary CAD, joints or contact.
"""
from __future__ import annotations

import math

SCHEMA = "bean.stress_reference.v1"


def _number(value, field, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"{field} must be finite" + (" and positive" if positive else ""))
    return result


def solve_stress_reference(request):
    """Return the physical stress tensor and von Mises at the requested y,z.

    Shaft axis is +X. sigma_x=Fx/A + My*z/I - Mz*y/I.
    tau_xy=-Tx*z/J; tau_xz=Tx*y/J. Moments in N*mm, stresses in MPa.
    """
    if not isinstance(request, dict) or request.get("schema") != "bean.stress_request.v1":
        raise ValueError("Unknown BEAN engineering request schema")
    if set(request) - {"schema", "geometry", "loads", "point_mm", "source_ref"}:
        raise ValueError("Unknown stress reference input fields")
    geom = request.get("geometry")
    loads = request.get("loads")
    if not isinstance(geom, dict) or geom.get("shape") != "solid_circular_shaft" or set(geom) != {"shape", "radius_mm"}:
        raise ValueError("Only solid_circular_shaft geometry is supported")
    if not isinstance(loads, dict) or set(loads) != {
        "axial_force_n", "bending_moment_y_nmm", "bending_moment_z_nmm", "torque_x_nmm"
    }:
        raise ValueError("Explicit axial, bending and torsional load components are required")
    radius = _number(geom["radius_mm"], "radius_mm", positive=True)
    f = _number(loads["axial_force_n"], "axial_force_n")
    my = _number(loads["bending_moment_y_nmm"], "bending_moment_y_nmm")
    mz = _number(loads["bending_moment_z_nmm"], "bending_moment_z_nmm")
    tx = _number(loads["torque_x_nmm"], "torque_x_nmm")
    pt = request.get("point_mm")
    if not isinstance(pt, (tuple, list)) or len(pt) != 2:
        raise ValueError("point_mm must contain y and z coordinates relative to shaft center")
    y, z = (_number(pt[0], "point_mm[0]"), _number(pt[1], "point_mm[1]"))
    if math.hypot(y, z) > radius*(1+1e-12):
        raise ValueError("Stress sampling point is outside the circular section")
    source_ref = request.get("source_ref")
    if source_ref is not None and (not isinstance(source_ref, str) or len(source_ref) > 200):
        raise ValueError("source_ref must be a short reference string")

    area = math.pi*radius**2
    inertia = math.pi*radius**4/4
    polar = 2*inertia
    sigma = f/area + my*z/inertia - mz*y/inertia
    tau_xy = -tx*z/polar
    tau_xz = tx*y/polar
    vm = math.hypot(sigma, math.sqrt(3)*math.hypot(tau_xy,tau_xz))
    if not all(math.isfinite(v) for v in (area,inertia,polar,sigma,tau_xy,tau_xz,vm)):
        raise ValueError("Computed reference overflowed; no stress result released")
    return {
        "schema": SCHEMA,
        "status": "calculated_reference_not_validated",
        "method": "closed_form_solid_circular_shaft_axial_bending_torsion",
        "source_ref": source_ref,
        "units": {"force": "N", "length": "mm", "moment": "N*mm", "stress": "MPa"},
        "section": {"area_mm2":area, "bending_inertia_mm4":inertia,
                    "polar_inertia_mm4":polar},
        "sample_point_yz_mm": [y,z],
        "tensor_mpa": {"sxx":sigma, "syy":0., "szz":0.,
                       "sxy":tau_xy, "sxz":tau_xz, "syz":0.},
        "von_mises_mpa": vm,
        "assumptions": [
            "Solid circular shaft and small-strain linear elasticity",
            "Idealized 1D axial and bending stresses plus Saint-Venant torsion",
            "No transverse shear forces, local end effects or stress concentrations",
            "No welds, joints, fasteners, contact or plasticity",
        ],
        "engineering_validation": "not_established",
        "trained_surrogate": False,
        "review_required": True,
    }
