"""BEAN Jobsite: field-readable lumber takeoff and weak-member screening.

No unsupported building-code defaults. Engineering numerical reference only.
Beam screening assumes a simply supported, straight rectangular elastic beam
subject to a uniformly distributed *line* load. Project-supplied allowable
limits are REQUIRED before comparison; this does not cover connectors,
bearing, buckling, combined load, creep, moisture, stability or code approval.
"""
from __future__ import annotations

import argparse
import json
import math
from importlib.resources import files
from pathlib import Path


def rules_catalog():
    with files("bean.engineering").joinpath("construction_rules.json").open(
        "r", encoding="utf-8"
    ) as fh:
        rules = json.load(fh)
    if rules.get("schema") != "bean.construction_rules.v1":
        raise ValueError("Unsupported jobsite rules catalog version")
    return rules


def _number(value, name, *, positive=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: enter a number")
    v = float(value)
    if not math.isfinite(v) or (positive and v <= 0) or (not positive and v < 0):
        raise ValueError(f"{name}: enter a finite {'positive' if positive else 'nonnegative'} number")
    return v


def count_studs(length_ft, spacing_in, *, openings=0):
    """Base full-height stud count for one straight wall without openings."""
    length_ft = _number(length_ft, "wall length (feet)")
    spacing_in = _number(spacing_in, "stud spacing (inches)")
    if type(openings) is not int or openings != 0:
        raise ValueError("Openings need a reviewed layout for headers/cripples; do not guess a stud count.")
    # Avoid an extra stud when a decimal representation is near an exact spacing multiple.
    spaces = length_ft * 12 / spacing_in
    studs = math.ceil(spaces - 1.0e-10) + 1
    return {
        "schema": "bean.jobsite_studs.v1",
        "rule_id": rules_catalog()["rules"]["straight_wall_takeoff"]["rule_id"],
        "wall_length_ft": length_ft,
        "spacing_in": spacing_in,
        "base_full_height_studs": studs,
        "material": "nominal 2x4 only when caller chooses that material",
        "additional_materials_not_included": [
            "top/bottom plates", "corners", "intersections", "door/window openings",
            "headers", "king/jack/cripple studs", "bracing/blocking", "waste",
        ],
        "building_code_compliant": False,
        "meaning": "quantity takeoff only; no load-bearing capacity determined",
    }


def _member(record, defaults):
    if not isinstance(record, dict):
        raise ValueError("Each beam must have labeled dimensions and loads")
    name = record.get("id")
    if not isinstance(name, str) or not name.strip() or len(name) > 80:
        raise ValueError("Each member needs a short nonempty ID")
    width = record.get("width_in")
    depth = record.get("depth_in")
    size = record.get("nominal_size")
    if size is not None:
        if size != "2x4" or width is not None or depth is not None:
            raise ValueError("Only the 2x4 nominal geometry reference is available; provide actual width/depth otherwise")
        dims = rules_catalog()["nominal_size_reference"]["2x4"]
        width, depth = dims["actual_width_in"], dims["actual_depth_in"]
    b = _number(width, f"{name}: actual width")
    h = _number(depth, f"{name}: actual depth")
    span_ft = _number(record.get("span_ft"), f"{name}: span")
    load_plf = _number(record.get("load_plf"), f"{name}: uniform load", positive=False)
    def parameter(key):
        raw = record[key] if key in record else defaults.get(key)
        return _number(raw, f"{name}: {key}")
    # These values must be provided, not inferred from the nominal lumber size.
    modulus = parameter("modulus_psi")
    fb = parameter("allowable_bending_psi")
    fv = parameter("allowable_shear_psi")
    deflection_ratio = parameter("deflection_limit_ratio")
    if deflection_ratio <= 1:
        raise ValueError(f"{name}: deflection limit must be a span/positive denominator > 1")
    L = span_ft * 12
    w = load_plf / 12
    I = b*h**3/12
    S = b*h**2/6
    moment = w*L**2/8
    shear_force = w*L/2
    stress = moment/S
    shear_stress = 1.5*shear_force/(b*h)
    deflection = 5*w*L**4/(384*modulus*I)
    allowed_deflection = L/deflection_ratio
    utilisations = {
        "bending": stress/fb,
        "shear": shear_stress/fv,
        "deflection": deflection/allowed_deflection,
    }
    if not all(math.isfinite(v) for v in (
        I, S, moment, shear_force, stress, shear_stress, deflection,
        allowed_deflection, *utilisations.values()
    )):
        raise ValueError(f"{name}: numerical overflow; invalid member comparison")
    governing = max(utilisations, key=utilisations.__getitem__)
    # Theoretical minimum depth for an otherwise unchanged, ideal, rectangular
    # member at each user-supplied threshold. Not a stocked lumber recommendation.
    required_h = {
        "bending": math.sqrt(6*moment/(b*fb)),
        "shear": 1.5*shear_force/(b*fv),
        "deflection": (5*w*L**4/(32*modulus*b*allowed_deflection))**(1/3),
    }
    min_depth = max(required_h.values())
    return {
        "id": name,
        "geometry_in": {"width": b, "depth": h, "span": L},
        "load_plf": load_plf,
        "calculated": {
            "peak_moment_lb_in": moment, "peak_shear_lb": shear_force,
            "bending_stress_psi": stress, "shear_stress_psi": shear_stress,
            "deflection_in": deflection,
        },
        "supplied_bounds": {"bending_psi": fb, "shear_psi": fv,
                            "deflection_in": allowed_deflection,
                            "elastic_modulus_psi": modulus},
        "utilization": utilisations,
        "worst_utilization": utilisations[governing],
        "governing": governing,
        "screen_status": "over_supplied_limit" if utilisations[governing] > 1 else "within_supplied_limits",
        "minimum_idealized_depth_in": min_depth,
        "screen_warning": ("Unbraced stability, bearing, end fixity, connections, "
                           "code load combinations and material adjustment factors are not evaluated"),
    }


def analyze_beams(members, project_defaults=None):
    """Rank the *most utilized*, not just the smallest or weakest-size beam."""
    if not isinstance(members, list) or not 1 <= len(members) <= 100:
        raise ValueError("Provide 1 to 100 actual beam members")
    if project_defaults is None:
        project_defaults = {}
    if not isinstance(project_defaults, dict):
        raise ValueError("Project design limits must be an object")
    candidates = [_member(item, project_defaults) for item in members]
    if len({item["id"] for item in candidates}) != len(candidates):
        raise ValueError("Beam names must be unique")
    ranked = sorted(candidates, key=lambda x: (-x["worst_utilization"], x["id"]))
    issues = [x for x in ranked if x["worst_utilization"] > 1]
    mitigations = []
    if issues:
        worst = issues[0]
        mitigations = [
            {
                "option": "Increase approved member depth or section stiffness",
                "why": f"{worst['id']} governs on {worst['governing']}",
                "reference": (f"At current loads and width, idealized depth >= "
                              f"{worst['minimum_idealized_depth_in']:.2f} in meets supplied scalar limits only"),
                "needs_check": "Select an actual grade/section, then re-check stability, connections, support bearing and building-code loads",
            },
            {
                "option": "Reduce unsupported span with a designed load path",
                "why": "Shorter span reduces simple-beam bending moment and deflection",
                "needs_check": "Added support requires foundation and reaction verification; continuous beams need a different analysis",
            },
            {
                "option": "Reduce tributary loading or add separately supported members",
                "why": "Less line load reduces stress and deflection in this model",
                "needs_check": "Verify load sharing, member spacing, connectors and revised load combinations",
            },
        ]
    return {
        "schema": "bean.jobsite_beam_screen.v1",
        "rule_id": rules_catalog()["rules"]["simply_supported_uniform_beam"]["rule_id"],
        "members": candidates,
        "weakest_member_by_utilization": ranked[0]["id"],
        "ranking": [x["id"] for x in ranked],
        "over_limit_members": [x["id"] for x in issues],
        "mitigations": mitigations,
        "method": "simply supported uniform-load elastic rectangular member (1D)",
        "status": "engineering_review_required" if issues else "screen_only_within_supplied_limits",
        "building_code_compliant": False,
        "real_fea_solve_performed": False,
        "training_weights_updated": False,
        "requires_qualified_review": True,
    }


def evaluate_request(request):
    if not isinstance(request, dict) or request.get("schema") != "bean.jobsite_request.v1":
        raise ValueError("BEAN Jobsite requires an explicit versioned request")
    operation = request.get("operation")
    if operation == "wall_studs":
        if set(request) - {"schema", "operation", "length_ft", "spacing_in", "openings"}:
            raise ValueError("Unknown wall takeoff fields")
        return count_studs(request.get("length_ft"), request.get("spacing_in"),
                           openings=request.get("openings", 0))
    if operation == "beam_check":
        if set(request) - {"schema", "operation", "members", "project_defaults"}:
            raise ValueError("Unknown beam-check fields")
        return analyze_beams(request.get("members"), request.get("project_defaults"))
    raise ValueError("Unsupported jobsite operation")


def _prompt(label):
    return float(input(label + ": ").strip())


def main():
    parser = argparse.ArgumentParser(description="BEAN Jobsite: quick count or weak-beam screening")
    parser.add_argument("--file", help="Versioned jobsite request JSON; useful for many beams")
    args = parser.parse_args()
    if args.file:
        report = evaluate_request(json.loads(Path(args.file).read_text(encoding="utf-8")))
        print(json.dumps(report, indent=2))
        return
    print("BEAN JOBSITE | 1 = count 2x4 studs | 2 = check one beam | Q = quit")
    while True:
        cmd = input("Choose 1, 2 or Q: ").strip().lower()
        if cmd in {"q", "quit", "3"}:
            break
        try:
            if cmd == "1":
                report = count_studs(_prompt("Straight wall length (feet)"),
                                     _prompt("Stud spacing on center (inches)"))
                print(f"BASE COUNT: {report['base_full_height_studs']} full-height studs.")
                print("Add plates, corners, openings, bracing and waste separately. Not a structural design.\n")
            elif cmd == "2":
                name = input("Member label: ").strip()
                fields = {
                    "id": name,
                    "width_in": _prompt("Actual member width (inches)"),
                    "depth_in": _prompt("Actual member depth, vertical (inches)"),
                    "span_ft": _prompt("Unsupported span (feet)"),
                    "load_plf": _prompt("Uniform load on beam (lb per foot)"),
                    "modulus_psi": _prompt("Approved material E (psi)"),
                    "allowable_bending_psi": _prompt("Approved bending limit (psi)"),
                    "allowable_shear_psi": _prompt("Approved shear limit (psi)"),
                    "deflection_limit_ratio": _prompt("Allowed deflection L/what number"),
                }
                report = analyze_beams([fields])
                entry = report["members"][0]
                print(f"{name}: {entry['governing']} = {entry['worst_utilization']*100:.1f}% of supplied limit.")
                print("Over limits: " + (", ".join(report["over_limit_members"]) or "none in this simplified screen"))
                if report["mitigations"]:
                    for suggestion in report["mitigations"]:
                        print("TRY: " + suggestion["option"] + ". " + suggestion["needs_check"])
                print("Engineering review required; this is not a code approval.\n")
            else:
                print("Choose 1, 2 or Q.\n")
        except (ValueError, KeyError) as exc:
            print(f"NEED BETTER INPUT: {exc}\n")


if __name__ == "__main__":
    main()
