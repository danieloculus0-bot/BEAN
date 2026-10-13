"""BEAN spatial optimization: bounded 2D layout and simulated route planning.

Pure planning calculations only. Hardware safety and validation remain separate.
"""
from .geometry import Rect, collision
from .routing import RouteResult, shortest_path
from .optimizer import (Object2D, Movable, MaterialFlow, AccessRoute,
                        SpatialProblem, Layout, validate_layout, optimize_layout)

__all__ = ["Rect", "collision", "RouteResult", "shortest_path", "Object2D",
           "Movable", "MaterialFlow", "AccessRoute", "SpatialProblem", "Layout",
           "validate_layout", "optimize_layout"]
