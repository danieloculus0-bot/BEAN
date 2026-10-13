"""Deterministic BEAN spatial tests for apartment, factory, and robot routes."""
import math
import pytest

from bean.spatial import (Rect, collision, shortest_path, Object2D, Movable,
                          MaterialFlow, AccessRoute, SpatialProblem,
                          optimize_layout, validate_layout)


def test_geometry_rejects_bad_dimensions_and_nonfinite():
    for args in [(0, 0, 0, 4), (0, 0, -3, 5), (0, math.nan, 1, 1)]:
        with pytest.raises(ValueError):
            Rect(*args)


def test_edges_touch_but_do_not_overlap():
    assert not collision(Rect(0, 0, 10, 10), Rect(10, 0, 5, 5))
    assert collision(Rect(0, 0, 10, 10), Rect(10, 0, 5, 5), a_clearance=1)


def test_route_blocked_wall():
    result = shortest_path(Rect(0, 0, 100, 60), [Rect(45, 0, 10, 60)], (10, 30), (90, 30))
    assert not result.found


def test_robot_routes_around_column_and_never_uses_obstacle():
    room = Rect(0, 0, 120, 100)
    obstacle = Rect(48, 25, 24, 50)
    route = shortest_path(room, [obstacle], (10, 50), (110, 50), radius=5, resolution=5)
    assert route.found and route.distance > 100
    assert all(not obstacle.expanded(5).contains_point(p) for p in route.points)


def test_robot_footprint_changes_corridor_feasibility():
    room = Rect(0, 0, 100, 50)
    ceiling = Rect(35, 0, 30, 15)
    floor = Rect(35, 35, 30, 15)
    assert shortest_path(room, [ceiling, floor], (10, 25), (90, 25), radius=5, resolution=5).found
    assert not shortest_path(room, [ceiling, floor], (10, 25), (90, 25), radius=11, resolution=5).found


def test_reject_bed_in_doorway():
    room = Rect(0, 0, 199, 132)
    problem = SpatialProblem(room, (), (Movable("sofa", 124, 86, (Rect(0, 0, 156, 132),)),))
    errors = validate_layout(problem, (Object2D("sofa", Rect(30, 0, 124, 86)),))
    assert not errors  # geometric fit alone cannot prove usable access
    problem = SpatialProblem(room, (Object2D("door_swing", Rect(0, 0, 43, 50)),),
                             (Movable("sofa", 124, 86),))
    assert any("Collision" in e for e in validate_layout(problem, (Object2D("sofa", Rect(30, 0, 124, 86)),)))


def test_apartment_fit_with_real_dimensions_and_fixed_kitchen():
    # Room coordinate axes deliberately abstracted. Doorway is a clearance zone.
    p = SpatialProblem(
        Rect(0, 0, 199, 132),
        (Object2D("kitchen_clearance", Rect(0, 0, 43, 48)),),
        (Movable("sectional", 124, 86, zones=(Rect(43, 0, 156, 132),),
                 preferred=(43, 0), preference_weight=3),),
        grid_step=8,
    )
    layouts = optimize_layout(p, top_k=2)
    assert layouts
    assert not validate_layout(p, layouts[0].placements)
    assert layouts[0].as_dict()["sectional"].x >= 43


def test_unmeasured_access_blocks_a_certificate():
    p = SpatialProblem(Rect(0, 0, 100, 60), (),
                       (Movable("large_machine", 80, 60),),
                       access=(AccessRoute((5, 30), (95, 30), radius=5),))
    assert optimize_layout(p) == []


def factory_problem():
    return SpatialProblem(
        room=Rect(0, 0, 360, 240),
        fixed=(Object2D("receiving", Rect(5, 90, 35, 60)),
               Object2D("shipping", Rect(320, 90, 35, 60)),
               Object2D("column", Rect(165, 90, 25, 45))),
        movable=(
            Movable("laser", 46, 35, zones=(Rect(65, 15, 95, 185),), preferred=(80, 30)),
            Movable("brake", 45, 40, zones=(Rect(205, 15, 100, 185),), preferred=(235, 35)),
        ),
        flows=(MaterialFlow("receiving", "laser", 2),
               MaterialFlow("laser", "brake", 2),
               MaterialFlow("brake", "shipping", 2)),
        access=(AccessRoute((50, 120), (310, 120), radius=8, resolution=5),),
        grid_step=20,
    )


def test_factory_layout_preserves_forklift_route():
    p = factory_problem()
    layouts = optimize_layout(p, top_k=2, beam_width=200)
    assert layouts, "Expected at least one layout with a verified simulated route"
    for layout in layouts:
        assert not validate_layout(p, layout.placements)
        assert all(p.room.contains(o.rect) for o in layout.placements)


def test_factory_invalid_collision_is_detected():
    p = factory_problem()
    placements = (Object2D("laser", Rect(165, 90, 46, 35)), Object2D("brake", Rect(235, 35, 45, 40)))
    assert any("Collision" in e for e in validate_layout(p, placements, check_routes=False))


def test_repeatability():
    p = factory_problem()
    a = optimize_layout(p, beam_width=120)
    b = optimize_layout(p, beam_width=120)
    assert a == b


def test_candidate_bounds_must_be_positive():
    with pytest.raises(ValueError):
        optimize_layout(factory_problem(), beam_width=0)


def test_optimization_returns_empty_when_space_insufficient():
    p = SpatialProblem(Rect(0, 0, 50, 50), (), (Movable("machine", 60, 60),))
    assert not optimize_layout(p)


def test_optimization_does_not_infer_hardware_safety():
    p = factory_problem()
    assert isinstance(optimize_layout(p)[0].score, float)
    assert not hasattr(optimize_layout(p)[0], "approved")
