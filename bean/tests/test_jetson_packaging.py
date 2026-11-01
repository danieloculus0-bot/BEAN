"""Portable Jetson packaging checks. No hardware, sudo, or real service writes."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from install.jetson_render import render_template
from scripts.jetson_runtime_audit import inspect_source, scrub

ROOT = Path(__file__).resolve().parents[2]
VALUES = {
    "BEAN_USER": "jetson",
    "BEAN_GROUP": "jetson",
    "BEAN_HOME": "/home/jetson/BEAN",
    "BEAN_DATA_DIR": "/home/jetson/bean_data",
    "BEAN_LOG_DIR": "/home/jetson/bean_logs",
    "BEAN_ENV_FILE": "/etc/bean/bean.env",
}


def test_render_service_for_actual_login():
    result = render_template("service", VALUES)
    assert "User=jetson" in result
    assert "WorkingDirectory=/home/jetson/BEAN" in result
    assert "ExecStart=/home/jetson/BEAN/.venv/bin/python3 /home/jetson/BEAN/bean_run.py" in result
    assert "EnvironmentFile=/etc/bean/bean.env" in result
    assert "@" not in result


def test_render_offline_env_with_persistent_memory():
    result = render_template("env", VALUES)
    assert "BEAN_DB_PATH=/home/jetson/bean_data/bean_memory.db" in result
    assert "BEAN_LOCAL_LLM_URL=http://127.0.0.1:8080" in result
    assert "BEAN_REASONING_PROVIDER=local_llamacpp" in result
    assert "@" not in result


@pytest.mark.parametrize("path", ("/tmp/../etc/bad", "relative/path", "/tmp/bad path"))
def test_render_rejects_unsafe_paths(path):
    changed = dict(VALUES, BEAN_HOME=path)
    with pytest.raises(ValueError):
        render_template("service", changed)


def test_render_rejects_unrecognized_username():
    with pytest.raises(ValueError):
        render_template("service", dict(VALUES, BEAN_USER="bad name"))


def test_jetson_installer_shell_syntax():
    if not shutil.which("bash"):
        pytest.skip("bash unavailable on this test host")
    subprocess.run(["bash", "-n", str(ROOT / "install/jetson_brain_install.sh")], check=True)


def test_source_wiring_inventory_uses_existing_code():
    data = inspect_source(ROOT)
    assert data["python_modules_on_disk"] > 50
    assert data["entrypoint_import_references"] > 10
    assert "inbox" in data["declared_periodic_handlers"]
    assert "status" in data["declared_inbox_command_examples"]
    assert not data["syntax_error_files"]


def test_scrub_does_not_publish_credentials():
    assert "notsafe" not in scrub("token=notsafe")
