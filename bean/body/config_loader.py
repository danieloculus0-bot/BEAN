"""
bean/body/config_loader.py

Finds and loads the body registry config file.
Handles path resolution, validation, and useful error messages.

Priority order for config location:
  1. Explicit path passed to load()
  2. BEAN_BODY_CONFIG env var
  3. bean/config/body_registry.json (next to repo)
  4. bean/config/body_registry.example.json (fallback for dev/test)

Never silently falls back without logging which file was used.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional

# Repo-relative config paths
_REPO_ROOT = Path(__file__).parent.parent
_CONFIG_DIR = _REPO_ROOT / "config"
_DEFAULT_CONFIG = _CONFIG_DIR / "body_registry.json"
_EXAMPLE_CONFIG = _CONFIG_DIR / "body_registry.example.json"

REQUIRED_TOP_KEYS = {"joints", "limbs"}
REQUIRED_JOINT_KEYS = {"joint_id", "label", "neutral_pos", "limits"}
REQUIRED_LIMIT_KEYS = {"min_pos", "max_pos"}


def find_config() -> Path:
    """
    Locate the body config file using the priority order above.
    Returns the resolved Path. Raises FileNotFoundError if nothing found.
    """
    # 1. Env var
    env_path = os.environ.get("BEAN_BODY_CONFIG")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
        raise FileNotFoundError(
            f"BEAN_BODY_CONFIG is set to '{env_path}' but file does not exist."
        )

    # 2. Default config
    if _DEFAULT_CONFIG.exists():
        return _DEFAULT_CONFIG

    # 3. Example config (dev/test fallback)
    if _EXAMPLE_CONFIG.exists():
        print(
            f"[BEAN body] WARNING: Using example body config: {_EXAMPLE_CONFIG}\n"
            f"  Copy to {_DEFAULT_CONFIG} and edit for your hardware."
        )
        return _EXAMPLE_CONFIG

    raise FileNotFoundError(
        f"No body config found. Expected one of:\n"
        f"  {_DEFAULT_CONFIG}\n"
        f"  {_EXAMPLE_CONFIG}\n"
        f"  or set BEAN_BODY_CONFIG=/path/to/body_registry.json"
    )


def load_raw(path: Optional[str] = None) -> tuple[dict, str]:
    """
    Load and return (raw_dict, resolved_path_str).
    Validates top-level structure. Does not validate joint details
    (that's the registry's job).
    """
    resolved = Path(path) if path else find_config()
    if not resolved.exists():
        raise FileNotFoundError(f"Body config not found: {resolved}")

    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Body config is not valid JSON: {resolved}\n  {e}")

    _validate_structure(raw, str(resolved))
    return raw, str(resolved)


def _validate_structure(raw: dict, path: str):
    """Basic structural validation before handing off to registry."""
    missing_top = REQUIRED_TOP_KEYS - set(raw.keys())
    if missing_top:
        raise ValueError(
            f"Body config missing required top-level keys: {missing_top}\n  in {path}"
        )

    if not isinstance(raw["joints"], list):
        raise ValueError(f"'joints' must be a list in {path}")
    if not isinstance(raw["limbs"], list):
        raise ValueError(f"'limbs' must be a list in {path}")

    for i, joint in enumerate(raw["joints"]):
        missing = REQUIRED_JOINT_KEYS - set(joint.keys())
        if missing:
            raise ValueError(
                f"Joint #{i} missing required keys {missing} in {path}"
            )
        limits = joint.get("limits", {})
        missing_limits = REQUIRED_LIMIT_KEYS - set(limits.keys())
        if missing_limits:
            raise ValueError(
                f"Joint '{joint.get('joint_id', i)}' limits missing "
                f"required keys {missing_limits} in {path}"
            )


def load_registry(path: Optional[str] = None):
    """
    Convenience: load config and initialize the global body registry.
    Returns the initialized BodyRegistry.
    """
    from .registry import init_registry_from_dict
    raw, resolved_path = load_raw(path)
    registry = init_registry_from_dict(raw)
    print(f"[BEAN body] Loaded body registry from: {resolved_path}")
    print(f"  {len(raw['joints'])} joint(s), {len(raw['limbs'])} limb(s)")
    return registry
