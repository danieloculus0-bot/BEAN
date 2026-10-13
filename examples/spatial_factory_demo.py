"""Run: python -m examples.spatial_factory_demo

A dimensioned *hypothetical* factory. Geometry is in inches, not scaled from
any actual facility. No machine motion or facility safety certification.
"""
from bean.spatial import (Rect, Object2D, Movable, MaterialFlow, AccessRoute,
                          SpatialProblem, optimize_layout, validate_layout,
                          shortest_path)


def main() -> int:
    problem = SpatialProblem(
        room=Rect(0, 0, 360, 240),
        fixed=(Object2D("receiving", Rect(5, 90, 35, 60)),
               Object2D("shipping", Rect(320, 90, 35, 60)),
               Object2D("column", Rect(165, 90, 25, 45))),
        movable=(Movable("laser", 46, 35, zones=(Rect(65, 15, 95, 185),), preferred=(80, 30)),
                 Movable("press_brake", 45, 40, zones=(Rect(205, 15, 100, 185),), preferred=(235, 35))),
        flows=(MaterialFlow("receiving", "laser", 2),
               MaterialFlow("laser", "press_brake", 2),
               MaterialFlow("press_brake", "shipping", 2)),
        access=(AccessRoute((50, 120), (310, 120), radius=8, resolution=5),),
        grid_step=20,
    )
    results = optimize_layout(problem, top_k=3, beam_width=200)
    if not results:
        print("NO VERIFIED SIMULATED LAYOUT at the given search settings")
        return 1
    for rank, result in enumerate(results, 1):
        assert not validate_layout(problem, result.placements)
        route = shortest_path(problem.room, [o.rect for o in (*problem.fixed, *result.placements)],
                              problem.access[0].start, problem.access[0].goal,
                              radius=problem.access[0].radius, resolution=problem.access[0].resolution)
        print(f"LAYOUT {rank}: cost={result.score:.2f}; route={route.distance:.2f} in; simulation only")
        for o in result.placements:
            print(f"  {o.name}: x={o.rect.x}, y={o.rect.y}, w={o.rect.width}, h={o.rect.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
