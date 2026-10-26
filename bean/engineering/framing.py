"""Position-based straight-wall stud takeoff with explicitly detailed openings.

Quantities are a MATERIAL ESTIMATE, never structural sufficiency, adopted
framing code, or a substitute for a complete elevation. No arbitrary
jack/king/cripple counts are assumed from an opening's appearance.
"""
from __future__ import annotations

import math

SCHEMA = "bean.jobsite_wall_layout.v1"
MAX_GRID_LOCATIONS = 10000
MAX_OPENINGS = 100


def _number(v, label, *, nonnegative=False):
    if type(v) not in (int, float) or not math.isfinite(v):
        raise ValueError(f"{label} needs a finite number")
    if v < 0 if nonnegative else v <= 0:
        raise ValueError(f"{label} must be {'nonnegative' if nonnegative else 'positive'}")
    return float(v)


def _count(v, label):
    if type(v) is not int or not 0 <= v <= 20:
        raise ValueError(f"{label} must be a whole number from 0 to 20")
    return v


def takeoff_wall(length_ft, spacing_in, openings):
    """Calculate grid removals plus explicitly specified supplemental pieces.

    Opening start and width are measured along the wall from its left end.
    Baseline stud centers exactly on opening boundaries are retained, so the
    caller MUST enter only the number of ADDITIONAL king studs beyond that
    retained framing; no implied doubling is inferred.
    """
    length_ft = _number(length_ft, "wall length")
    spacing_in = _number(spacing_in, "stud spacing")
    if not isinstance(openings, list) or len(openings) > MAX_OPENINGS:
        raise ValueError("openings must be a list of at most 100 explicit rough openings")
    length_in = length_ft * 12
    if not math.isfinite(length_in):
        raise ValueError("Wall length overflow")
    # Include one at each end, even if the final interval is shorter.
    intervals = length_in / spacing_in
    if not math.isfinite(intervals) or intervals >= MAX_GRID_LOCATIONS:
        raise ValueError("Wall has too many grid locations; split it into segments")
    intervals_full = int(math.floor(intervals + 1e-10))
    positions = [n * spacing_in for n in range(intervals_full + 1)]
    if length_in - positions[-1] > max(1e-8, length_in*1e-12):
        positions.append(length_in)
    else:
        positions[-1] = length_in
    tolerance = max(1e-8, length_in*1e-12)
    details = []
    for index, opening in enumerate(openings, start=1):
        if not isinstance(opening, dict) or set(opening) != {
            "start_in", "width_in", "extra_king_studs_per_side", "jack_studs_per_side"
        }:
            raise ValueError(f"Opening {index} needs start/width and explicit king/jack counts")
        start = _number(opening["start_in"], f"Opening {index} start")
        width = _number(opening["width_in"], f"Opening {index} width")
        kings = _count(opening["extra_king_studs_per_side"], f"Opening {index} extra kings")
        jacks = _count(opening["jack_studs_per_side"], f"Opening {index} jacks")
        end = start + width
        if not math.isfinite(end) or start <= tolerance or end >= length_in-tolerance:
            raise ValueError(f"Opening {index} touches an end or extends outside wall; use a detailed corner/edge layout")
        details.append((start, end, kings, jacks))
    ordered = sorted(details)
    for previous, following in zip(ordered, ordered[1:]):
        if following[0] <= previous[1] + tolerance:
            raise ValueError("Openings overlap or touch; supply an engineered shared-framing detail")
    removed = [position for position in positions if any(
        start+tolerance < position < end-tolerance
        for start, end, _, _ in ordered
    )]
    baseline = len(positions)
    kings = sum(2 * v[2] for v in details)
    jacks = sum(2 * v[3] for v in details)
    remaining = baseline - len(removed)
    total = remaining + kings + jacks
    return {
        "schema": SCHEMA,
        "rule_id": "quantity.explicit_opening_wall_takeoff.v1",
        "wall_length_ft": length_ft,
        "spacing_in": spacing_in,
        "baseline_grid_studs": baseline,
        "studs_removed_inside_rough_openings": len(removed),
        "baseline_full_height_studs_remaining": remaining,
        "extra_full_height_king_studs_specified": kings,
        "short_jack_studs_specified": jacks,
        # Each counted item is a separate framing SEGMENT, not a purchased
        # full-length board. Stock-length optimization requires wall height,
        # jack lengths, cuts, waste and the actual lumber supplier dimensions.
        "minimum_specified_2x4_pieces_before_other_framing": total,
        "purchased_stock_board_count": None,
        "opening_count": len(details),
        "removed_center_positions_in": removed,
        "openings": [
            {"start_in": start, "width_in": end-start,
             "extra_king_studs_per_side": k, "jack_studs_per_side": j}
            for start, end, k, j in details
        ],
        "not_included": [
            "top/bottom plates", "headers", "cripples above/below openings",
            "blocking and bracing", "corners and intersections",
            "waste/cuts", "actual stud lengths", "fasteners",
        ],
        "notes": [
            "Kings listed are EXTRA to the retained full-height grid positions; check elevation to avoid double counting",
            "Boundary grid studs are retained; this takeoff does not decide whether they are proper kings",
            "Jack/king quantities are caller-supplied, not code-derived",
            "Number of framing segments is NOT the number of full-length lumber boards to purchase",
        ],
        "building_code_compliant": False,
        "load_capacity_checked": False,
        "requires_verified_framing_plan": True,
    }
