"""Boot readiness smoke test for BEAN OS rebuilds."""

from __future__ import annotations


def test_boot_readiness_temp_db_passes():
    from bean.runtime.boot_readiness import run_boot_readiness_check
    report = run_boot_readiness_check(use_temp_db=True)
    assert report["success"] is True
    assert report["motion_enabled"] is False
    assert report["physical_output_enabled"] is False
    assert report["checks"]["core_memory"] is True
    assert report["checks"]["origin_covenant"] is True
    assert report["checks"]["capability_sync"] is True
    assert report["checks"]["boundary_sync"] is True
    assert report["checks"]["event_log"] is True
    assert report["checks"]["relationship_schema"] is True
    assert report["checks"]["wisdom_probe"] is True
    assert report["checks"]["reasoning_probe"] is True
    assert report["checks"]["hypothesis_probe"] is True
    assert report["checks"]["runtime_proof"] is True
    assert report["missing_capabilities"] == []
    assert report["missing_boundaries"] == []
    assert report["counts"]["events"] >= 1
    assert report["counts"]["capabilities"] >= 1
    assert report["counts"]["boundaries"] >= 1


def test_boot_readiness_reports_platform():
    from bean.runtime.boot_readiness import run_boot_readiness_check
    report = run_boot_readiness_check(use_temp_db=True)
    assert "platform" in report
    assert "system" in report["platform"]
    assert "python" in report["platform"]
    assert "jetson_l4t_detected" in report["platform"]


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    failed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"PASS {name}")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            import traceback
            traceback.print_exc()
    raise SystemExit(1 if failed else 0)
