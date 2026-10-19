"""Core cognition is exposed as reusable blocks; Bridge composes them."""
from .builtin import BLOCKS, register_builtin

__all__ = ["BLOCKS", "register_builtin"]
