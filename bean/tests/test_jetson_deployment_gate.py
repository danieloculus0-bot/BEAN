"""Static, no-device tests for the read-only Jetson installation gate."""
from install.jetson_deployment_gate import _service_entries, assess


def _ready():
    return {
        "system": "Linux",
        "architecture": "aarch64",
        "model": "NVIDIA Jetson Orin Nano Super Developer Kit",
        "python_ok": True,
        "venv": True,
        "pip": True,
        "systemd": True,
        "user_exists": True,
        "service_matches": True,
        "available_disk_gib": 8.5,
    }


def test_ready_fixture_never_claims_iso_or_hardware_boot():
    result = assess(_ready())
    assert result["status"] == "READY_FOR_BEAN_INSTALL"
    assert not result["blockers"]
    for name in ("iso_image_verified", "physical_boot_verified", "uefi_qspi_compatibility_verified", "motion_or_motor_output_tested"):
        assert result[name] is False


def test_legacy_nano_is_not_orin_nano():
    host = _ready()
    host["model"] = "NVIDIA Jetson Nano Developer Kit"
    result = assess(host)
    assert result["status"] == "BLOCKED"
    assert "orin_nano_model" in result["blockers"]


def test_wrong_architecture_rejected():
    host = _ready()
    host["architecture"] = "x86_64"
    result = assess(host)
    assert "arm64" in result["blockers"]


def test_old_python_and_missing_dependencies_reported():
    host = _ready()
    host.update(python_ok=False, pip=False, venv=False)
    result = assess(host)
    assert {"python_3_10_plus", "python_pip", "python_venv"} <= set(result["blockers"])


def test_uncreated_user_or_mismatched_systemd_install_blocked():
    host = _ready()
    host["user_exists"] = False
    host["service_matches"] = False
    result = assess(host)
    assert {"service_user_exists", "installer_paths_consistent"} <= set(result["blockers"])


def test_insufficient_work_space_blocked():
    host = _ready()
    host["available_disk_gib"] = 1.75
    assert "workspace_free_2_gib" in assess(host)["blockers"]


def test_service_field_parser_does_not_confuse_section_or_comments():
    service = "[Service]\n#User=wrong\nUser=bean\nGroup=bean\nWorkingDirectory=/home/bean/BEAN\n"
    parsed = _service_entries(service)
    assert parsed["User"] == "bean"
    assert parsed["Group"] == "bean"
    assert "Service" not in parsed
