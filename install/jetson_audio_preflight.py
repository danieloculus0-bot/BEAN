#!/usr/bin/env python3
"""Read-only Jetson audio inventory for BEAN Rev 1 and new Core launch.

Does not record, play audio, select system defaults or launch another brain.
No third-party Python dependency in the inspector itself.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess


def run(argv: list[str], *, timeout: int = 8) -> dict[str, object]:
    if not shutil.which(argv[0]):
        return {"available": False, "returncode": None, "output": "not installed"}
    try:
        result = subprocess.run(argv, capture_output=True, text=True,
                                timeout=timeout, errors="replace", check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "returncode": None, "output": type(exc).__name__}
    return {"available": True, "returncode": result.returncode,
            "output": (result.stdout + result.stderr)[:4000].strip()}


def inspect(*, user_home: Path | None = None) -> dict:
    home = user_home or Path.home()
    capture = run(["arecord", "-l"])
    playback = run(["aplay", "-l"])
    legacy = home / "BEAN" / "bean_voice.py"
    model = home / "vosk-model-small-en-us-0.15"
    env_python = home / "beanenv" / "bin" / "python"

    result = {
        "mode": "read_only_no_audio_recorded_or_played",
        "capture": capture,
        "playback": playback,
        "alsa_cards": (Path("/proc/asound/cards").read_text(errors="replace")[:2000]
                       if Path("/proc/asound/cards").is_file() else "Unavailable"),
        "speech_tools": {
            "espeak_ng": shutil.which("espeak-ng") is not None,
            "piper": shutil.which("piper") is not None,
            "pico2wave": shutil.which("pico2wave") is not None,
        },
        "legacy": {
            "voice_script": str(legacy) if legacy.is_file() else None,
            "python_venv": str(env_python) if env_python.is_file() else None,
            "vosk_model": str(model) if model.is_dir() else None,
        },
        "python_audio": {"available": False, "devices": [], "error": "No legacy Python venv"},
    }
    if env_python.is_file():
        check = (
            "import json, sounddevice as sd;"
            "print(json.dumps([{'index': i, 'name': d['name'],"
            "'inputs': d['max_input_channels'], 'outputs': d['max_output_channels']}"
            " for i,d in enumerate(sd.query_devices())"
            " if d['max_input_channels'] or d['max_output_channels']]))"
        )
        try:
            proc = subprocess.run([str(env_python), "-c", check], capture_output=True,
                                  text=True, timeout=8, check=False)
            if proc.returncode == 0:
                result["python_audio"] = {"available": True,
                                          "devices": json.loads(proc.stdout), "error": None}
            else:
                result["python_audio"] = {"available": False, "devices": [],
                                          "error": proc.stderr.strip()[:500]}
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            result["python_audio"] = {"available": False, "devices": [],
                                      "error": type(exc).__name__}

    result["hints"] = [
        "The prior working microphone was the USB webcam; inspect the ALSA card number above.",
        "The prior working playback was HDMI; card/device assignments can change on reboot.",
        "Previously tested routes: mic plughw:0,0; HDMI plughw:1,3 (not guaranteed now).",
        "Vosk needs mono 16000 Hz and model vosk-model-small-en-us-0.15.",
        "Old bean_voice.py also used Ollama; it must not auto-start alongside the new Core.",
    ]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="BEAN Jetson audio device inventory")
    parser.add_argument("--json", action="store_true", help="machine-readable result")
    args = parser.parse_args()
    details = inspect()
    if args.json:
        print(json.dumps(details, indent=2))
        return 0
    print("BEAN Jetson audio inventory (read-only)")
    for kind in ("capture", "playback"):
        value = details[kind]
        print(f"\n{kind.upper()}:")
        print(value["output"] if value["available"] else "ALSA utility missing")
    print("\nLEGACY VOICE:")
    for key, value in details["legacy"].items():
        print(f"  {key}: {value or 'not found'}")
    print("\nSPEECH TOOLS:")
    for key, value in details["speech_tools"].items():
        print(f"  {key}: {'found' if value else 'not found'}")
    print("\nPORTAUDIO DEVICES:")
    if details["python_audio"]["available"]:
        for dev in details["python_audio"]["devices"]:
            print(f"  [{dev['index']}] {dev['name']} (in={dev['inputs']}, out={dev['outputs']})")
    else:
        print(f"  {details['python_audio']['error']}")
    print("\nIMPORTANT:")
    for hint in details["hints"]:
        print("  " + hint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
