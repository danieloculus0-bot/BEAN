"""Installer contract regression tests that never install/enable a service."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "install" / "jetson_brain_install.sh"


def test_jetson_installer_bash_syntax():
    completed = subprocess.run(["bash", "-n", str(INSTALLER)], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr


def test_jetson_installer_rejects_override_before_sudo_or_disk_changes():
    environment = os.environ.copy()
    environment["BEAN_USER"] = "somebody"
    completed = subprocess.run(
        ["bash", str(INSTALLER)], cwd=ROOT, env=environment, capture_output=True, text=True,
        timeout=10,
    )
    assert completed.returncode != 0
    assert "BEAN_USER=bean only" in completed.stderr


def test_jetson_installer_rejects_wrong_service_location_early():
    environment = os.environ.copy()
    environment["BEAN_HOME"] = "/tmp/not-bean"
    completed = subprocess.run(
        ["bash", str(INSTALLER)], cwd=ROOT, env=environment, capture_output=True, text=True,
        timeout=10,
    )
    assert completed.returncode != 0
    assert "BEAN_HOME=/home/bean/BEAN" in completed.stderr
