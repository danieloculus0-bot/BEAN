"""
bean/runtime/monitor.py

Runtime system monitor for BEAN.
Reads real OS-backed hardware/resource state when available and records it
without inventing values. Missing readings are None, not fake zeros.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import psutil  # type: ignore
    _PSUTIL_AVAILABLE = True
except Exception:
    psutil = None
    _PSUTIL_AVAILABLE = False

from ..memory.store import get_store
from ..memory.event_logger import log_event, EventType, Source, Severity

CPU_WARN_THRESHOLD = 90.0
RAM_WARN_THRESHOLD = 85.0
DISK_WARN_THRESHOLD = 90.0
TEMP_WARN_THRESHOLD = 70.0
TEMP_ERROR_THRESHOLD = 85.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BodyStateReading:
    timestamp: str
    cpu_percent: Optional[float]
    ram_percent: Optional[float]
    ram_used_mb: Optional[float]
    ram_total_mb: Optional[float]
    gpu_percent: Optional[float]
    disk_percent: Optional[float]
    disk_free_gb: Optional[float]
    temperature_c: Optional[float]
    uptime_seconds: Optional[float]
    power_mode: Optional[str]
    read_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"timestamp": self.timestamp, "cpu_percent": self.cpu_percent, "ram_percent": self.ram_percent, "ram_used_mb": self.ram_used_mb, "ram_total_mb": self.ram_total_mb, "gpu_percent": self.gpu_percent, "disk_percent": self.disk_percent, "disk_free_gb": self.disk_free_gb, "temperature_c": self.temperature_c, "uptime_seconds": self.uptime_seconds, "power_mode": self.power_mode, "read_errors": self.read_errors}

    def anomalies(self) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        if self.cpu_percent is not None and self.cpu_percent > CPU_WARN_THRESHOLD:
            found.append(("warn", f"CPU high: {self.cpu_percent:.1f}%"))
        if self.ram_percent is not None and self.ram_percent > RAM_WARN_THRESHOLD:
            found.append(("warn", f"RAM high: {self.ram_percent:.1f}%"))
        if self.disk_percent is not None and self.disk_percent > DISK_WARN_THRESHOLD:
            found.append(("warn", f"Disk high: {self.disk_percent:.1f}%"))
        if self.temperature_c is not None:
            if self.temperature_c > TEMP_ERROR_THRESHOLD:
                found.append(("error", f"Temperature critical: {self.temperature_c:.1f}C"))
            elif self.temperature_c > TEMP_WARN_THRESHOLD:
                found.append(("warn", f"Temperature high: {self.temperature_c:.1f}C"))
        return found


class SystemMonitor:
    def __init__(self):
        self.last_reading: Optional[BodyStateReading] = None

    def read(self) -> BodyStateReading:
        errors: list[str] = []
        cpu = ram_percent = ram_used = ram_total = None
        disk_percent = disk_free = None
        uptime = None
        if _PSUTIL_AVAILABLE:
            try:
                cpu = float(psutil.cpu_percent(interval=None))
            except Exception as e:
                errors.append(f"cpu_percent: {e}")
            try:
                vm = psutil.virtual_memory()
                ram_percent = float(vm.percent)
                ram_used = float(vm.used) / (1024 * 1024)
                ram_total = float(vm.total) / (1024 * 1024)
            except Exception as e:
                errors.append(f"memory: {e}")
            try:
                du = psutil.disk_usage("/")
                disk_percent = float(du.percent)
                disk_free = float(du.free) / (1024 ** 3)
            except Exception as e:
                errors.append(f"disk: {e}")
            try:
                uptime = time.time() - float(psutil.boot_time())
            except Exception as e:
                errors.append(f"uptime: {e}")
        else:
            try:
                load = os.getloadavg()[0]
                cpu = max(0.0, min(100.0, (load / max(1, os.cpu_count() or 1)) * 100.0))
            except Exception as e:
                errors.append(f"cpu_fallback: {e}")
            try:
                uptime = float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
            except Exception as e:
                errors.append(f"uptime_fallback: {e}")
        reading = BodyStateReading(_now(), cpu, ram_percent, ram_used, ram_total, self._read_gpu_percent(errors), disk_percent, disk_free, self._read_temperature(errors), uptime, self._read_power_mode(errors), errors)
        self.last_reading = reading
        return reading

    def _read_temperature(self, errors: list[str]) -> Optional[float]:
        for path in ("/sys/devices/virtual/thermal/thermal_zone0/temp", "/sys/class/thermal/thermal_zone0/temp"):
            try:
                if os.path.exists(path):
                    raw = Path(path).read_text(encoding="utf-8").strip()
                    value = float(raw)
                    return value / 1000.0 if value > 200 else value
            except Exception as e:
                errors.append(f"temperature:{path}: {e}")
        if _PSUTIL_AVAILABLE:
            try:
                temps = psutil.sensors_temperatures() or {}
                for entries in temps.values():
                    if entries:
                        return float(entries[0].current)
            except Exception as e:
                errors.append(f"psutil_temperature: {e}")
        return None

    def _read_gpu_percent(self, errors: list[str]) -> Optional[float]:
        try:
            out = subprocess.run(["tegrastats", "--interval", "100", "--count", "1"], capture_output=True, text=True, timeout=1.5)
            text = out.stdout + out.stderr
            if "GR3D_FREQ" in text:
                chunk = text.split("GR3D_FREQ", 1)[1]
                digits = "".join(ch for ch in chunk if ch.isdigit() or ch == "%")
                if "%" in digits:
                    return float(digits.split("%", 1)[0])
        except FileNotFoundError:
            return None
        except Exception as e:
            errors.append(f"gpu: {e}")
        return None

    def _read_power_mode(self, errors: list[str]) -> Optional[str]:
        try:
            out = subprocess.run(["nvpmodel", "-q"], capture_output=True, text=True, timeout=1.5)
            for line in out.stdout.splitlines():
                if "NV Power Mode" in line or "Power Mode" in line:
                    return line.strip()
        except FileNotFoundError:
            return None
        except Exception as e:
            errors.append(f"power_mode: {e}")
        return None

    def read_and_log(self, session_uuid: str) -> BodyStateReading:
        reading = self.read()
        store = get_store()
        store.execute("""
            INSERT INTO body_state
                (session_uuid, cpu_percent, ram_percent, gpu_percent, disk_percent,
                 temperature_c, power_state, motor_state, uptime_seconds, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_uuid, reading.cpu_percent, reading.ram_percent, reading.gpu_percent, reading.disk_percent, reading.temperature_c, reading.power_mode, None, reading.uptime_seconds, "runtime_monitor"))
        store.commit()
        log_event(session_uuid=session_uuid, event_type=EventType.BODY_STATE, subtype="system_monitor_reading", summary="Runtime system monitor reading recorded.", source=Source.SENSOR, data=reading.to_dict())
        for severity, message in reading.anomalies():
            log_event(session_uuid=session_uuid, event_type=EventType.WARNING if severity == "warn" else EventType.ERROR, subtype="hardware_anomaly", summary=message, source=Source.SENSOR, severity=Severity.WARN if severity == "warn" else Severity.ERROR, data=reading.to_dict())
        return reading
