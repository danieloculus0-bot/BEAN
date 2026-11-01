"""Jetson/USB-Arduino adapter for BEAN's existing motion registry and limits.

ACK confirms the Arduino accepted a PWM target, not that a servo moved.
Requires pyserial only when opening a real serial port.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bean.body.registry import BodyRegistry
    from bean.body.state import BodyState
    from bean.motion.command import MotionCommand
    from bean.motion.safety import MotionSafety


class MotionHardwareError(RuntimeError):
    """Rejected command, missing calibration, or controller exchange failure."""


@dataclass(frozen=True)
class ServoCalibration:
    """Measured pulses at the registry joint's absolute min and max angles."""

    pulse_at_min_us: int
    pulse_at_max_us: int

    def __post_init__(self):
        for value in (self.pulse_at_min_us, self.pulse_at_max_us):
            if type(value) is not int or not 500 <= value <= 2500:
                raise ValueError("Calibration pulse must be an integer in 500..2500 us")
        if self.pulse_at_min_us == self.pulse_at_max_us:
            raise ValueError("Calibration endpoints must be distinct")

    def pulse_for(self, position: float, min_pos: float, max_pos: float) -> int:
        if not all(math.isfinite(v) for v in (position, min_pos, max_pos)):
            raise ValueError("Position and limits must be finite")
        if min_pos >= max_pos or not min_pos <= position <= max_pos:
            raise ValueError("Position outside calibrated mechanical limits")
        ratio = (position - min_pos) / (max_pos - min_pos)
        return round(self.pulse_at_min_us + ratio * (self.pulse_at_max_us - self.pulse_at_min_us))


def load_calibrations(path: str | Path) -> dict[str, ServoCalibration]:
    """Explicit local hardware config; no guessed default servo mapping."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("Calibration file must be a nonempty joint-id mapping")
    result = {}
    for joint_id, values in data.items():
        if not isinstance(joint_id, str) or not joint_id or not isinstance(values, dict):
            raise ValueError("Expected a joint-id to calibration object mapping")
        result[joint_id] = ServoCalibration(
            pulse_at_min_us=values["pulse_at_min_us"],
            pulse_at_max_us=values["pulse_at_max_us"],
        )
    return result


@dataclass(frozen=True)
class MotionDispatch:
    joint_id: str
    channel: int
    requested_position: float
    pulse_us: int
    sequence: int
    accepted_by_controller: bool = True
    position_confirmed: bool = False


class ArduinoMotionBridge:
    """Translate an approved BEAN joint command to PCA9685 PWM over serial.

    transport implements write(bytes) and readline() -> bytes.
    """

    def __init__(
        self,
        registry: BodyRegistry,
        safety: MotionSafety,
        transport,
        calibrations: dict[str, ServoCalibration],
        body_state: BodyState | None = None,
    ):
        self.registry = registry
        self.safety = safety
        self.transport = transport
        self.calibrations = calibrations
        self.body_state = body_state
        self._sequence = 0

    def handshake(self, attempts: int = 12) -> None:
        """Allow for Arduino USB bootloader reset and verify protocol v1."""
        for _ in range(attempts):
            self.transport.write(b"HELLO\n")
            reply = self.transport.readline().strip()
            if reply == b"READY 1":
                return
        raise MotionHardwareError("Arduino motion protocol did not become ready")

    def send(self, command: MotionCommand, *, current_pos: float | None = None) -> MotionDispatch:
        from bean.motion.command import CommandIntent

        if command.intent not in (CommandIntent.MOVE_TO, CommandIntent.MOVE_BY, CommandIntent.NEUTRAL):
            raise MotionHardwareError(f"Unsupported hardware intent: {command.intent}")
        if not math.isfinite(command.target_pos) or not math.isfinite(command.speed):
            raise MotionHardwareError("Motion command contains nonfinite values")

        verdict = self.safety.check(command, current_pos=current_pos)
        if not verdict.approved or verdict.resolved_target is None:
            raise MotionHardwareError("MotionSafety rejected command: " + "; ".join(verdict.violations))

        joint = self.registry.get_joint(command.joint_id)
        if not joint.hardware_connected or joint.servo_channel is None:
            raise MotionHardwareError(f"Joint {command.joint_id} has no confirmed controller mapping")
        channel = joint.servo_channel
        if type(channel) is not int or not 0 <= channel < 16:
            raise MotionHardwareError("PCA9685 channel must be in 0..15")
        calibration = self.calibrations.get(command.joint_id)
        if calibration is None:
            raise MotionHardwareError(f"No pulse calibration for {command.joint_id}")

        position = verdict.resolved_target
        pulse = calibration.pulse_for(position, joint.limits.min_pos, joint.limits.max_pos)
        self._sequence += 1
        seq = self._sequence
        self.transport.write(f"M,{seq},{channel},{pulse}\n".encode("ascii"))
        for _ in range(8):
            line = self.transport.readline().strip()
            if line == f"ACK,{seq}".encode("ascii"):
                if self.body_state is not None:
                    from bean.body.joint import JointStateKind
                    self.body_state._state_map.update(
                        joint_id=command.joint_id,
                        position=position,
                        kind=JointStateKind.ESTIMATED,
                        notes="Arduino accepted PWM target; no position sensor confirmation.",
                    )
                return MotionDispatch(command.joint_id, channel, position, pulse, seq)
            if line.startswith(f"ERR,{seq},".encode("ascii")):
                raise MotionHardwareError(line.decode("ascii", errors="replace"))
            if not line:
                break
        raise MotionHardwareError(f"No matching Arduino ACK for motion sequence {seq}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Move one calibrated BEAN joint via USB Arduino")
    parser.add_argument("--port", required=True, help="e.g. /dev/ttyACM0")
    parser.add_argument("--body", required=True, help="actual BEAN body_registry.json")
    parser.add_argument("--calibration", required=True, help="private joint pulse calibration JSON")
    parser.add_argument("--joint", required=True)
    parser.add_argument("--position", required=True, type=float)
    parser.add_argument("--speed", type=float, default=10.0)
    args = parser.parse_args()

    from bean.body.registry import BodyRegistry
    from bean.body.state import BodyState
    from bean.motion.command import MotionCommand
    from bean.motion.safety import MotionSafety

    try:
        import serial
    except ImportError as exc:
        parser.error("pyserial is required for USB hardware: python -m pip install pyserial")
        raise AssertionError from exc

    registry = BodyRegistry().load(args.body)
    state = BodyState(registry)
    calibrations = load_calibrations(args.calibration)
    with serial.Serial(args.port, baudrate=115200, timeout=0.4, write_timeout=2) as transport:
        bridge = ArduinoMotionBridge(registry, MotionSafety(registry), transport, calibrations, state)
        bridge.handshake()
        result = bridge.send(MotionCommand.move_to(args.joint, args.position, args.speed))
    print(json.dumps(result.__dict__, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
