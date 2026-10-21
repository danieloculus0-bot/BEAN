#!/usr/bin/env python3
"""Read-only post-OS-install gate for BEAN on Jetson Orin Nano Super.

This is not an ISO builder, firmware updater, or hardware actuator. It checks
whether the machine is a plausible target for BEAN's *existing* installer.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
import sys
from pathlib import Path


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip("\x00\n ")
    except OSError:
        return ""


def _service_entries(service: str) -> dict[str, str]:
    """Read the plain scalar fields used by our versioned systemd template."""
    entries = {}
    for line in service.splitlines():
        line = line.strip()
        if line.startswith(("#", "[")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        entries[key] = value
    return entries


def inspect_host(repo_root: Path | None = None) -> dict:
    root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    user = os.environ.get("BEAN_USER", "bean")
    home = os.environ.get("BEAN_HOME", "/home/bean/BEAN")
    env_file = os.environ.get("ENV_FILE", "/etc/bean/bean.env")
    service = _service_entries(_read(root / "install" / "bean.service"))
    try:
        import pwd
        account = pwd.getpwnam(user)
        user_exists = True
        group_name = __import__("grp").getgrgid(account.pw_gid).gr_name
    except (ImportError, KeyError):
        user_exists = False
        group_name = None

    service_matches = (
        service.get("User") == user
        and service.get("Group") == group_name
        and service.get("WorkingDirectory") == home
        and service.get("EnvironmentFile") == env_file
        and service.get("ExecStart") == f"{home}/.venv/bin/python3 {home}/bean_run.py"
        and str(root) == home
    )
    return {
        "system": platform.system(),
        "architecture": platform.machine().lower(),
        "model": _read(Path("/proc/device-tree/model")),
        "l4t_release": _read(Path("/etc/nv_tegra_release")),
        "python": platform.python_version(),
        "python_ok": sys.version_info >= (3, 10),
        "venv": importlib.util.find_spec("venv") is not None,
        "pip": importlib.util.find_spec("pip") is not None,
        "systemd": shutil.which("systemctl") is not None,
        "user": user,
        "user_exists": user_exists,
        "service_matches": service_matches,
        "repo_root": str(root),
        "expected_home": home,
        "available_disk_gib": round(shutil.disk_usage(root).free / (1024 ** 3), 2),
    }


def assess(facts: dict) -> dict:
    model = facts.get("model", "").lower()
    checks = {
        "linux": facts.get("system") == "Linux",
        "arm64": facts.get("architecture") in ("aarch64", "arm64"),
        "orin_nano_model": "jetson orin nano" in model,
        "python_3_10_plus": bool(facts.get("python_ok")),
        "python_venv": bool(facts.get("venv")),
        "python_pip": bool(facts.get("pip")),
        "systemd_available": bool(facts.get("systemd")),
        "service_user_exists": bool(facts.get("user_exists")),
        "installer_paths_consistent": bool(facts.get("service_matches")),
        "workspace_free_2_gib": facts.get("available_disk_gib", 0) >= 2.0,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "READY_FOR_BEAN_INSTALL" if not failures else "BLOCKED",
        "checks": checks,
        "blockers": failures,
        "host": facts,
        "evidence_scope": "POST_JETSON_LINUX_INSTALL_ONLY",
        "physical_boot_verified": False,
        "iso_image_verified": False,
        "uefi_qspi_compatibility_verified": False,
        "motion_or_motor_output_tested": False,
        "notes": [
            "NVIDIA Jetson ISO must already have installed Jetson Linux; this is not an ISO boot test.",
            "Firmware compatibility and media integrity require separate independent evidence.",
            "No hardware output is accessed or enabled by this script.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only BEAN Jetson Orin Nano post-install readiness gate")
    parser.add_argument("--report", type=Path, help="Optional path for exact JSON receipt; no write if omitted")
    args = parser.parse_args()
    result = assess(inspect_host())
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "READY_FOR_BEAN_INSTALL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
