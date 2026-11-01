"""Portable Jetson packaging checks. No hardware, sudo, or real service writes."""
from __future__ import annotations

import getpass
import grp
import os
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


def test_render_local_cuda_inference_unit():
    vals = dict(VALUES, BEAN_LLAMACPP_DIR="/home/jetson/llama.cpp/build-bean-cuda",
                BEAN_GGUF_PATH="/home/jetson/bean_core_data/models/qwen.gguf",
                BEAN_LLM_PORT="8080")
    result = render_template("llm_service", vals)
    assert "User=jetson" in result
    assert "--model /home/jetson/bean_core_data/models/qwen.gguf" in result
    assert "--host 127.0.0.1 --port 8080 --alias bean-local" in result
    assert "ExecStart=/home/jetson/llama.cpp/build-bean-cuda/bin/llama-server" in result
    assert "@" not in result


@pytest.mark.parametrize("port", ("abc", "80", "65536"))
def test_invalid_model_service_port_rejected(port):
    vals = dict(VALUES, BEAN_LLAMACPP_DIR="/tmp/llama/build",
                BEAN_GGUF_PATH="/tmp/bean.gguf", BEAN_LLM_PORT=port)
    with pytest.raises(ValueError):
        render_template("llm_service", vals)


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
    for filename in ("jetson_brain_install.sh", "jetson_local_llm_install.sh"):
        subprocess.run(["bash", "-n", str(ROOT / "install" / filename)], check=True)


def test_source_wiring_inventory_uses_existing_code():
    data = inspect_source(ROOT)
    assert data["python_modules_on_disk"] > 50
    assert data["entrypoint_import_references"] > 10
    assert "inbox" in data["declared_periodic_handlers"]
    assert "status" in data["declared_inbox_command_examples"]
    assert not data["syntax_error_files"]


def test_scrub_does_not_publish_credentials():
    assert "notsafe" not in scrub("token=notsafe")



def test_mocked_cuda_package_install_reuses_source_and_writes_service(tmp_path):
    """Exercise the real shell orchestration with fake nvcc/cmake/systemctl.

    Proves compiler path propagation and correct service rendering without
    touching actual Jetson hardware, sudo, model downloads or real services.
    """
    binaries = tmp_path / "bin"
    binaries.mkdir()
    llama_root = tmp_path / "llama.cpp"
    (llama_root / ".git").mkdir(parents=True)
    cuda_bin = tmp_path / "cuda/bin"
    cuda_bin.mkdir(parents=True)
    nvcc = cuda_bin / "nvcc"
    nvcc.write_text("#!/bin/sh\nprintf 'nvcc mocked\\n'\n")
    nvcc.chmod(0o755)
    log = tmp_path / "cmake.log"
    cmake = binaries / "cmake"
    cmake.write_text(
        "#!/bin/bash\n"
        "printf '%s\\n' \"$*\" >> \"$BEAN_TEST_CMAKE_LOG\"\n"
        "if [[ \"$1\" == '--build' ]]; then\n"
        "  mkdir -p \"$2/bin\"\n"
        "  printf '#!/bin/sh\\nexit 0\\n' > \"$2/bin/llama-server\"\n"
        "  chmod +x \"$2/bin/llama-server\"\n"
        "fi\n"
    )
    cmake.chmod(0o755)
    sudo = binaries / "sudo"
    sudo.write_text("#!/bin/sh\nif [ \"$1\" = systemctl ]; then exit 0; fi\nexec \"$@\"\n")
    sudo.chmod(0o755)
    model = tmp_path / "models/qwen.gguf"
    model.parent.mkdir()
    model.write_bytes(b"GGUFmock-model")
    env = os.environ.copy()
    env.update({
        "PATH": str(binaries) + os.pathsep + env["PATH"],
        "BEAN_USER": getpass.getuser(),
        "BEAN_GROUP": grp.getgrgid(os.getgid()).gr_name,
        "BEAN_HOME": str(ROOT),
        "BEAN_DATA_DIR": str(tmp_path / "data"),
        "BEAN_LOG_DIR": str(tmp_path / "logs"),
        "ENV_FILE": str(tmp_path / "bean.env"),
        "BEAN_LLAMA_CPP_DIR": str(llama_root),
        "BEAN_LLAMA_BUILD_DIR": str(llama_root / "build-bean-cuda"),
        "BEAN_GGUF_PATH": str(model),
        "BEAN_LLM_SERVICE_FILE": str(tmp_path / "bean-llamacpp.service"),
        "BEAN_NVCC": str(nvcc),
        "BEAN_LLM_DOWNLOAD": "0",
        "BEAN_LLM_START": "0",
        "BEAN_TEST_CMAKE_LOG": str(log),
    })
    proc = subprocess.run(
        ["bash", str(ROOT / "install/jetson_local_llm_install.sh")],
        env=env, cwd=str(ROOT), text=True, capture_output=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    calls = log.read_text()
    assert "-DGGML_CUDA=ON" in calls
    assert f"-DCMAKE_CUDA_COMPILER={nvcc.resolve()}" in calls
    assert "-DCMAKE_CUDA_ARCHITECTURES=87" in calls
    assert "build-bean-cuda" in calls
    service = (tmp_path / "bean-llamacpp.service").read_text()
    assert "--alias bean-local" in service
    assert f"--model {model}" in service
    assert f"ExecStart={llama_root}/build-bean-cuda/bin/llama-server" in service
