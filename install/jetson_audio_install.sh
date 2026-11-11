#!/usr/bin/env bash
# BEAN Jetson audio userspace prerequisites plus read-only device inspection.
# Does not replace NVIDIA kernel drivers, switch default devices, play audio,
# change ALSA/PulseAudio configurations, or start the old Ollama voice process.
set -euo pipefail

BEAN_HOME="${BEAN_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"
AUDIO_INSTALL="${BEAN_AUDIO_INSTALL:-1}"
AUDIO_SCAN="${BEAN_AUDIO_SCAN:-1}"
[[ "$AUDIO_INSTALL" == 0 || "$AUDIO_INSTALL" == 1 ]] ||
  { echo "BEAN_AUDIO_INSTALL must be 0 or 1" >&2; exit 1; }
[[ "$AUDIO_SCAN" == 0 || "$AUDIO_SCAN" == 1 ]] ||
  { echo "BEAN_AUDIO_SCAN must be 0 or 1" >&2; exit 1; }

packages=()
if ! command -v arecord >/dev/null 2>&1 ||
   ! command -v aplay >/dev/null 2>&1; then
  packages+=(alsa-utils)
fi
if ! command -v espeak-ng >/dev/null 2>&1; then
  packages+=(espeak-ng)
fi
if command -v dpkg-query >/dev/null 2>&1 &&
   ! dpkg-query -W -f='${Status}' libportaudio2 2>/dev/null | grep -q 'install ok installed'; then
  packages+=(libportaudio2)
fi

if (( ${#packages[@]} )); then
  if [[ "$AUDIO_INSTALL" == 1 ]]; then
    if ! command -v apt-get >/dev/null 2>&1; then
      echo "Cannot automatically install missing audio packages: ${packages[*]}" >&2
      exit 1
    fi
    echo "==> Installing missing ALSA/PortAudio/speech userspace packages: ${packages[*]}"
    sudo apt-get update
    sudo apt-get install -y "${packages[@]}"
  else
    echo "Audio prerequisites missing (BEAN_AUDIO_INSTALL=0): ${packages[*]}"
  fi
else
  echo "==> ALSA, PortAudio and eSpeak-NG prerequisites already installed"
fi

if [[ "$AUDIO_SCAN" == 1 ]]; then
  echo "==> Checking microphone, playback and original Vosk installation"
  python3 "$BEAN_HOME/install/jetson_audio_preflight.py"
fi

echo "Audio check complete. Existing sound defaults and BEAN Core are untouched."
