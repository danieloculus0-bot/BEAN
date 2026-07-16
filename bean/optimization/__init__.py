"""Brain 0.14 supervised self-optimization package."""

from .governor import SelfOptimizationGovernor, init_self_optimization_schema
from .proposal import OptimizationProposal


def init_self_optimization(conn=None) -> SelfOptimizationGovernor:
    return SelfOptimizationGovernor(conn)


__all__ = [
    "OptimizationProposal",
    "SelfOptimizationGovernor",
    "init_self_optimization",
    "init_self_optimization_schema",
]
