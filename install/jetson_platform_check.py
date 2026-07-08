#!/usr/bin/env python3
"""Jetson / JetPack platform check for BEAN installs.

This script is intentionally stdlib-only. It reports whether the machine looks
like an NVIDIA Jetson Linux / L4T system and whether the minimum BEAN runtime
assumptions are present. It does not touch hardware.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path


def _read(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return None


def inspect_platform() -> dict:
    nv_tegra = _read("/etc/nv_tegra_release")
    os_release = _read("/etc/os-release")
    machine = platform.machine()
    system = platform.system()
    python_version = sys.version_info
    is_linux = system == "Linux"
    is_arm64 = machine in {"aarch64", "arm64"}
    looks_like_jetson = bool(nv_tegra) or Path("/proc/device-tree/model").exists() and "NVIDIA" in (_read("/proc/device-tree/model") or "")

    checks = {
        "linux": is_linux,
        "arm64": is_arm64,
        "python_3_10_or_newer": python_version >= (3, 10),
        "venv_available": _venv_available(),
        "systemd_available": shutil.which("systemctl") is not None,
        "pip_available": shutil.which("pip3") is not None or shutil.which("python3") is not None,
        "jetson_l4t_detected": looks_like_jetson,
    }
    return {
        "success": checks["linux"] and checks["python_3_10_or_newer"] and checks["venv_available"],
        "platform": {"system": system, "machine": machine, "python": platform.python_version()},
        "checks": checks,
        "nv_tegra_release": nv_tegra,
        "os_release": os_release,
        "notes": [
            "Jetson/L4T detection is required for final BEAN OS install unless BEAN_ALLOW_NON_JETSON_INSTALL=1.",
            "No physical output hardware is enabled by this check.",
        ],
    }


def _venv_available() -> bool:
    try:
        import venv  # noqa: F401
        return True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Jetson / JetPack compatibility for BEAN.")
    parser.add_argument("--require-jetson", action="store_true", help="Fail unless Jetson/L4T is detected or BEAN_ALLOW_NON_JETSON_INSTALL=1.")
    args = parser.parse_args()
    report = inspect_platform()
    allow_non_jetson = os.environ.get("BEAN_ALLOW_NON_JETSON_INSTALL") == "1"
    if args.require_jetson and not report["checks"]["jetson_l4t_detected"] and not allow_non_jetson:
        report["success"] = False
        report.setdefault("errors", []).append("Jetson/L4T not detected. Set BEAN_ALLOW_NON_JETSON_INSTALL=1 only for development machines.")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
