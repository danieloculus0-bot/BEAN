"""Bounded beam-search optimizer for 2D furniture, factory and robot scenes.

All outputs are *simulated candidates*. No globally optimality guarantee,
real-world clearance certification, or actuator commands are implied.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite

from .geometry import Rect, collision
from .routing import Point, shortest_path


@dataclass(frozen=True)
class Object2D:
    name: str
    rect: Rect
    clearance: float = 0

    def __post_init__(self) -> None:
        if not self.name or not isfinite(self.clearance) or self.clearance < 0:
            raise ValueError("Named objects need non-negative finite clearance")


@dataclass(frozen=True)
class Movable:
    name: str
    width: float
    height: float
    zones: tuple[Rect, ...] = ()
    rotate: bool = False
    clearance: float = 0
    wall_clearance: float = 0
    preferred: Point | None = None
    preference_weight: float = 1

    def __post_init__(self) -> None:
        Rect(0, 0, self.width, self.height)
        if not self.name or any(not isfinite(v) or v < 0 for v in (self.clearance, self.wall_clearance, self.preference_weight)):
            raise ValueError("Invalid movable name, weight or clearance")
        if self.preferred is not None and not all(isfinite(v) for v in self.preferred):
            raise ValueError("Preferred origin must be finite")


@dataclass(frozen=True)
class MaterialFlow:
    source: str
    destination: str
    weight: float = 1

    def __post_init__(self) -> None:
        if not isfinite(self.weight) or self.weight < 0:
            raise ValueError("Flow weights must be non-negative finite")


@dataclass(frozen=True)
class AccessRoute:
    """Required path between two open-space points, including robot footprint."""
    start: Point
    goal: Point
    radius: float = 0
    resolution: float = 6


@dataclass(frozen=True)
class SpatialProblem:
    room: Rect
    fixed: tuple[Object2D, ...]
    movable: tuple[Movable, ...]
    flows: tuple[MaterialFlow, ...] = ()
    access: tuple[AccessRoute, ...] = ()
    grid_step: float = 12

    def __post_init__(self) -> None:
        if not isfinite(self.grid_step) or self.grid_step <= 0:
            raise ValueError("Grid step must be positive and finite")
        names = [o.name for o in self.fixed] + [o.name for o in self.movable]
        if len(names) != len(set(names)):
            raise ValueError("Object names must be unique")
        for f in self.flows:
            if f.source not in names or f.destination not in names:
                raise ValueError("Flows must reference named objects")


@dataclass(frozen=True)
class Layout:
    placements: tuple[Object2D, ...]
    score: float
    # Exhaustive optimum is NOT claimed. Bounds are imposed by beam width.

    def as_dict(self) -> dict[str, Rect]:
        return {o.name: o.rect for o in self.placements}


def _candidate_positions(room: Rect, item: Movable, step: float) -> list[Rect]:
    zones = item.zones or (room,)
    positions: dict[tuple[float, float, float, float], Rect] = {}
    sizes = [(item.width, item.height)]
    if item.rotate and item.width != item.height:
        sizes.append((item.height, item.width))
    for zone in zones:
        for width, height in sizes:
            if zone.width < width or zone.height < height:
                continue
            xcount = int((zone.width - width) / step)
            ycount = int((zone.height - height) / step)
            xs = [zone.x + i * step for i in range(xcount + 1)] + [zone.right - width]
            ys = [zone.y + i * step for i in range(ycount + 1)] + [zone.bottom - height]
            for x in xs:
                for y in ys:
                    r = Rect(x, y, width, height)
                    if room.contains(r.expanded(item.wall_clearance)) and zone.contains(r):
                        positions[(round(x, 7), round(y, 7), width, height)] = r
    result = list(positions.values())
    if item.preferred is not None:
        result.sort(key=lambda r: (hypot(r.x - item.preferred[0], r.y - item.preferred[1]), r.x, r.y))
    else:
        result.sort(key=lambda r: (r.x, r.y, r.width, r.height))
    return result


def _score(problem: SpatialProblem, placed: tuple[Object2D, ...]) -> float:
    lookup = {o.name: o.rect for o in (*problem.fixed, *placed)}
    result = 0.0
    defs = {o.name: o for o in problem.movable}
    for o in placed:
        item = defs[o.name]
        if item.preferred is not None:
            result += item.preference_weight * hypot(o.rect.x - item.preferred[0], o.rect.y - item.preferred[1])
    for f in problem.flows:
        if f.source in lookup and f.destination in lookup:
            a, b = lookup[f.source].center, lookup[f.destination].center
            result += f.weight * hypot(a[0] - b[0], a[1] - b[1])
    return result


def validate_layout(problem: SpatialProblem, placements: tuple[Object2D, ...] | list[Object2D], *,
                    check_routes: bool = True) -> list[str]:
    """Check geometry and mandatory routes; return reasons, never silently repair."""
    errors = []
    placed = tuple(placements)
    fixed = problem.fixed
    defs = {o.name: o for o in problem.movable}
    if sorted(o.name for o in placed) != sorted(defs):
        errors.append("Movable object names or counts do not match the problem")
    for o in fixed:
        if not problem.room.contains(o.rect):
            errors.append(f"Fixed object outside room: {o.name}")
    for o in placed:
        if o.name not in defs:
            continue
        m = defs[o.name]
        if not problem.room.contains(o.rect.expanded(m.wall_clearance)):
            errors.append(f"Outside bounds: {o.name}")
        if not any(z.contains(o.rect) for z in (m.zones or (problem.room,))):
            errors.append(f"Outside permitted zone: {o.name}")
        if (o.rect.width, o.rect.height) not in ((m.width, m.height), (m.height, m.width) if m.rotate else (m.width, m.height)):
            errors.append(f"Invalid orientation: {o.name}")
        if abs(o.clearance - m.clearance) > 1e-9:
            errors.append(f"Clearance mismatch: {o.name}")
    all_objects = (*fixed, *placed)
    for i, a in enumerate(all_objects):
        for b in all_objects[i + 1:]:
            if collision(a.rect, b.rect, a_clearance=a.clearance, b_clearance=b.clearance):
                errors.append(f"Collision: {a.name} with {b.name}")
    if check_routes and not errors:
        for index, access in enumerate(problem.access):
            route = shortest_path(problem.room, [o.rect for o in all_objects],
                                  access.start, access.goal,
                                  radius=access.radius, resolution=access.resolution)
            if not route.found:
                errors.append(f"No access route: {index}")
    return errors


def optimize_layout(problem: SpatialProblem, *, top_k: int = 3, beam_width: int = 80,
                    candidate_limit: int = 400) -> list[Layout]:
    """Rank valid candidates. Beam bounds make this heuristic, not a proof of global optimum."""
    if min(top_k, beam_width, candidate_limit) < 1:
        raise ValueError("Search budgets must be at least 1")
    if validate_layout(SpatialProblem(problem.room, problem.fixed, (), grid_step=problem.grid_step), ()):
        return []
    beam: list[tuple[Object2D, ...]] = [()]
    for item in problem.movable:
        candidates = _candidate_positions(problem.room, item, problem.grid_step)[:candidate_limit]
        next_states: list[tuple[Object2D, ...]] = []
        for state in beam:
            for r in candidates:
                new = Object2D(item.name, r, item.clearance)
                if any(collision(new.rect, old.rect, a_clearance=new.clearance, b_clearance=old.clearance)
                       for old in (*problem.fixed, *state)):
                    continue
                next_states.append((*state, new))
        next_states.sort(key=lambda s: (_score(problem, s), tuple((o.rect.x, o.rect.y, o.rect.width, o.rect.height) for o in s)))
        beam = next_states[:beam_width]
        if not beam:
            return []
    valid: list[Layout] = []
    for state in beam:
        if not validate_layout(problem, state):
            valid.append(Layout(state, _score(problem, state)))
        if len(valid) >= top_k:
            break
    return valid
