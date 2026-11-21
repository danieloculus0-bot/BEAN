"""Bounded 2D rigid-body spin and liquid-fill reference for BEAN.

General-purpose educational model: parts are point locations with optional
intrinsic polar moments; a vertical cylinder contains a rigidly co-rotating
homogeneous fluid approximation. The actual motion of a sloshing liquid is NOT
modelled. No proprietary geometry, external libraries or production claims.

Coordinate system: x horizontal, y up, spin axis perpendicular to x/y.
Units: kg, m, s, rad; fluid density in kg/L, capacity in liters.
"""
from __future__ import annotations

import math

SCHEMA = "bean.rigid_body_balance.v1"
G0 = 9.80665
MAX_PARTS = 128
MAX_FILL_SAMPLES = 101
MAX_PIVOTS = 301


def _real(value, name, *, positive=False, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    value = float(value)
    if positive and value <= 0 or nonnegative and value < 0:
        raise ValueError(f"{name} out of range")
    return value


def _point(raw, name):
    if not isinstance(raw, (tuple, list)) or len(raw) != 2:
        raise ValueError(f"{name} must have exactly two numbers")
    return (_real(raw[0], f"{name}[0]"), _real(raw[1], f"{name}[1]"))


def _parts(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_PARTS:
        raise ValueError("parts must contain 1 to 128 entries")
    result = []
    for i, part in enumerate(raw):
        if not isinstance(part, dict):
            raise ValueError(f"parts[{i}] must be an object")
        mass = _real(part.get("mass_kg"), f"parts[{i}].mass_kg", nonnegative=True)
        center = _point(part.get("center_m"), f"parts[{i}].center_m")
        inertia = _real(part.get("intrinsic_inertia_kg_m2", 0),
                        f"parts[{i}].intrinsic_inertia_kg_m2", nonnegative=True)
        result.append((mass, *center, inertia))
    return result


def _reservoir(raw):
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("reservoir must be an object")
    return {
        "capacity_l": _real(raw.get("capacity_l"), "capacity_l", positive=True),
        "inner_radius_m": _real(raw.get("inner_radius_m"), "inner_radius_m", positive=True),
        "base_center_m": _point(raw.get("base_center_m"), "base_center_m"),
        "fluid_density_kg_per_l": _real(raw.get("fluid_density_kg_per_l"), "fluid_density_kg_per_l", positive=True),
    }


def _liquid(r, fill):
    if r is None or fill == 0:
        return None
    height = (r["capacity_l"] / 1000 * fill) / (math.pi * r["inner_radius_m"]**2)
    mass = r["capacity_l"] * fill * r["fluid_density_kg_per_l"]
    inertia = mass * (3 * r["inner_radius_m"]**2 + height**2) / 12
    if not math.isfinite(height) or not math.isfinite(inertia):
        raise ValueError("reservoir dimensions overflow")
    x, y = r["base_center_m"]
    return mass, x, y + height/2, inertia


def _metrics(parts, reservoir, fill, pivot, spin_rps, gravity):
    liquid = _liquid(reservoir, fill)
    components = parts if liquid is None else parts + [liquid]
    mass = sum(c[0] for c in components)
    if mass <= 0:
        raise ValueError("total mass must be positive")
    cx = sum(c[0]*c[1] for c in components)/mass
    cy = sum(c[0]*c[2] for c in components)/mass
    off = math.hypot(cx-pivot[0], cy-pivot[1])
    iz = sum(c[3] + c[0]*((c[1]-pivot[0])**2 + (c[2]-pivot[1])**2) for c in components)
    omega = 2*math.pi*spin_rps
    values = (mass, cx, cy, off, iz, mass*gravity*off, mass*omega*omega*off)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("numeric overflow")
    return {"fill_fraction":fill,"mass_kg":mass,"center_of_mass_m":[cx,cy],
            "offset_m":off,"inertia_kg_m2":iz,
            "peak_gravity_torque_nm":mass*gravity*off,
            "radial_reaction_n":mass*omega*omega*off,
            "rotational_energy_j":0.5*iz*omega*omega}


def solve_rigid_body_balance(request):
    """Return a bounded, deterministic fill-state assessment and candidate comparison.

    Required: parts=[{mass_kg,center_m,[intrinsic_inertia_kg_m2]}].
    Optional: reservoir={capacity_l,inner_radius_m,base_center_m,fluid_density_kg_per_l};
      fill_fractions; pivot_m; spin_rps; gravity_m_s2; pivot_candidates_m;
      maximum_pivot_y_m (a geometry constraint supplied by caller).
    """
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    parts = _parts(request.get("parts"))
    reservoir = _reservoir(request.get("reservoir"))
    fills = request.get("fill_fractions", [0,.25,.5,.75,1])
    if not isinstance(fills, list) or not 1 <= len(fills) <= MAX_FILL_SAMPLES:
        raise ValueError("fill_fractions must contain 1 to 101 entries")
    fills = [_real(v,"fill_fraction",nonnegative=True) for v in fills]
    if any(f > 1 for f in fills):
        raise ValueError("fill fraction must be <= 1")
    pivot = _point(request.get("pivot_m", [0,0]), "pivot_m")
    speed = _real(request.get("spin_rps",1.0),"spin_rps",nonnegative=True)
    gravity = _real(request.get("gravity_m_s2",G0),"gravity_m_s2",positive=True)
    cap_y = request.get("maximum_pivot_y_m")
    if cap_y is not None:
        cap_y = _real(cap_y,"maximum_pivot_y_m")
    if cap_y is not None and pivot[1] > cap_y:
        raise ValueError("baseline pivot violates maximum_pivot_y_m")
    baseline = [_metrics(parts,reservoir,f,pivot,speed,gravity) for f in fills]
    pivot_raw = request.get("pivot_candidates_m",[])
    if not isinstance(pivot_raw,list) or len(pivot_raw)>MAX_PIVOTS:
        raise ValueError("pivot_candidates_m must be a list of at most 301")
    rankings = []
    for i,point in enumerate(pivot_raw):
        p = _point(point,f"pivot_candidates_m[{i}]")
        if cap_y is not None and p[1]>cap_y:
            continue
        states = [_metrics(parts,reservoir,f,p,speed,gravity) for f in fills]
        rankings.append({"pivot_m":list(p),
                         "worst_peak_gravity_torque_nm":max(s["peak_gravity_torque_nm"] for s in states),
                         "worst_offset_m":max(s["offset_m"] for s in states),
                         "worst_radial_reaction_n":max(s["radial_reaction_n"] for s in states)})
    rankings.sort(key=lambda p:(p["worst_peak_gravity_torque_nm"],p["worst_offset_m"],p["pivot_m"]))
    return {"schema":SCHEMA,"status":"simplified_synthetic_reference",
            "assumptions":["planar rigid-body motion","liquid co-rotates as a uniform cylinder",
                "no slosh, splashing, grip biomechanics, friction or structural flexibility"],
            "baseline_pivot_m":list(pivot),"spin_rps":speed,"states":baseline,
            "ranked_pivot_candidates":rankings,
            "recommended_candidate":rankings[0] if rankings else None}
