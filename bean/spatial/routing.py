"""Conservative, deterministic 2D axis-aligned grid routing.

Swept segments are checked against inflated obstacles. No hardware motion is
issued. A failure only means no route was found at the requested resolution.
"""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from math import hypot, isfinite

from .geometry import Rect

Point = tuple[float, float]


@dataclass(frozen=True)
class RouteResult:
    found: bool
    points: tuple[Point, ...] = ()
    distance: float | None = None
    explored: int = 0


def _segment_hits_rect(a: Point, b: Point, r: Rect) -> bool:
    """Closed-rectangle segment intersection; touching is conservatively blocked."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    lo, hi = 0.0, 1.0
    for p, q in ((-dx, a[0] - r.x), (dx, r.right - a[0]),
                 (-dy, a[1] - r.y), (dy, r.bottom - a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                lo = max(lo, t)
            else:
                hi = min(hi, t)
            if lo > hi:
                return False
    return True


def shortest_path(room: Rect, obstacles: tuple[Rect, ...] | list[Rect],
                  start: Point, goal: Point, *, radius: float = 0,
                  resolution: float = 5, max_nodes: int = 100000) -> RouteResult:
    """Find a collision-free 4-neighbor path from exact start to exact goal.

    Grid vertices are room-local positions; arbitrary endpoints connect to
    nearby grid vertices only if the entire connecting segment is free.
    """
    if not isfinite(resolution) or resolution <= 0:
        raise ValueError("resolution must be positive and finite")
    if not isfinite(radius) or radius < 0:
        raise ValueError("radius must be non-negative and finite")
    if max_nodes < 1:
        raise ValueError("max_nodes must be at least 1")
    if not all(isfinite(v) for v in (*start, *goal)):
        raise ValueError("Endpoints must be finite")
    safe_room = Rect(room.x + radius, room.y + radius,
                     room.width - 2 * radius, room.height - 2 * radius) if room.width > 2 * radius and room.height > 2 * radius else None
    if safe_room is None:
        return RouteResult(False)
    blocked = tuple(o.expanded(radius) for o in obstacles)

    def clear_point(p: Point) -> bool:
        return safe_room.contains_point(p) and not any(o.contains_point(p) for o in blocked)

    def clear_edge(a: Point, b: Point) -> bool:
        return clear_point(a) and clear_point(b) and not any(_segment_hits_rect(a, b, o) for o in blocked)

    if not clear_point(start) or not clear_point(goal):
        return RouteResult(False)
    if clear_edge(start, goal):
        return RouteResult(True, (start, goal), hypot(goal[0] - start[0], goal[1] - start[1]), 0)

    nx = int(room.width // resolution)
    ny = int(room.height // resolution)
    def point(node: tuple[int, int]) -> Point:
        return (room.x + node[0] * resolution, room.y + node[1] * resolution)

    def nearby(p: Point) -> list[tuple[int, int]]:
        i = (p[0] - room.x) / resolution
        j = (p[1] - room.y) / resolution
        ai, aj = int(i), int(j)
        candidates = {(u, v) for u in (ai - 1, ai, ai + 1, ai + 2)
                      for v in (aj - 1, aj, aj + 1, aj + 2)
                      if 0 <= u <= nx and 0 <= v <= ny}
        return sorted((n for n in candidates if clear_edge(p, point(n))),
                      key=lambda n: (hypot(p[0] - point(n)[0], p[1] - point(n)[1]), n))

    origin_neighbors = nearby(start)
    targets = nearby(goal)
    if not origin_neighbors or not targets:
        return RouteResult(False)
    goal_links = {n: hypot(point(n)[0] - goal[0], point(n)[1] - goal[1]) for n in targets}
    cost: dict[tuple[int, int], float] = {}
    previous: dict[tuple[int, int], tuple[int, int] | None] = {}
    heap: list[tuple[float, int, tuple[int, int]]] = []
    serial = count()
    for n in origin_neighbors:
        d = hypot(point(n)[0] - start[0], point(n)[1] - start[1])
        cost[n] = d
        previous[n] = None
        heappush(heap, (d + hypot(point(n)[0] - goal[0], point(n)[1] - goal[1]), next(serial), n))
    explored = 0
    finished = None
    while heap and explored < max_nodes:
        estimate, _, n = heappop(heap)
        if estimate > cost[n] + hypot(point(n)[0] - goal[0], point(n)[1] - goal[1]) + 1e-8:
            continue
        explored += 1
        if n in goal_links:
            finished = n
            break
        for d in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            m = (n[0] + d[0], n[1] + d[1])
            if not (0 <= m[0] <= nx and 0 <= m[1] <= ny):
                continue
            if not clear_edge(point(n), point(m)):
                continue
            next_cost = cost[n] + resolution
            if next_cost + 1e-8 < cost.get(m, float('inf')):
                cost[m] = next_cost
                previous[m] = n
                heappush(heap, (next_cost + hypot(point(m)[0] - goal[0], point(m)[1] - goal[1]), next(serial), m))
    if finished is None:
        return RouteResult(False, explored=explored)
    nodes = []
    n = finished
    while n is not None:
        nodes.append(point(n))
        n = previous[n]
    nodes.reverse()
    route = [start, *nodes, goal]
    simplified = [route[0]]
    for p in route[1:]:
        if p != simplified[-1]:
            simplified.append(p)
    length = sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(simplified, simplified[1:]))
    return RouteResult(True, tuple(simplified), length, explored)
