"""Windows offline microphone and synthesized voice, using built-in System.Speech.

Press Enter to listen. No continuous mic recording, file upload, model access,
or remote speech provider. All PowerShell commands are constant templates;
speech data is passed on stdin, never embedded into executable commands.
"""
from __future__ import annotations

import os
import subprocess
import sys


class SpeechError(RuntimeError):
    pass


TALK_SCRIPT = r"""
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
$reader = [Console]::In.ReadToEnd()
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if ($env:BEAN_VOICE_NAME) { $speaker.SelectVoice($env:BEAN_VOICE_NAME) }
    $speaker.Rate = [int]$env:BEAN_VOICE_RATE
    $speaker.Speak($reader)
} finally { $speaker.Dispose() }
"""

LISTEN_SCRIPT = r"""
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine
try {
    $grammar = New-Object System.Speech.Recognition.DictationGrammar
    $recognizer.LoadGrammar($grammar)
    $recognizer.SetInputToDefaultAudioDevice()
    $recognizer.InitialSilenceTimeout = [TimeSpan]::FromSeconds(7)
    $recognizer.EndSilenceTimeout = [TimeSpan]::FromMilliseconds(800)
    $heard = $recognizer.Recognize([TimeSpan]::FromSeconds(14))
    if ($null -ne $heard -and $heard.Confidence -ge 0.45) {
        [Console]::Out.Write($heard.Text)
    }
} finally { $recognizer.Dispose() }
"""


class WindowsSpeech:
    def __init__(self, *, name: str | None = None, rate: int = 0,
                 runner=None, platform: str | None = None):
        self.platform = platform or sys.platform
        if self.platform != "win32":
            raise SpeechError("Voice mode currently requires Windows PowerShell and Windows speech recognition")
        if not -10 <= rate <= 10:
            raise ValueError("Voice rate must be between -10 and 10")
        self.name = name
        self.rate = rate
        self._runner = runner or subprocess.run

    def _execute(self, script: str, *, spoken_text: str | None = None,
                 timeout: int = 35) -> str:
        env = os.environ.copy()
        env["BEAN_VOICE_NAME"] = self.name or ""
        env["BEAN_VOICE_RATE"] = str(self.rate)
        try:
            result = self._runner(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                input=spoken_text,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SpeechError("Windows speech engine could not start or timed out") from exc
        if result.returncode != 0:
            hint = (result.stderr or "").strip().splitlines()
            excerpt = hint[-1][:180] if hint else "speech device or voice not available"
            raise SpeechError("Windows speech engine error: " + excerpt)
        return result.stdout.strip()

    def speak(self, message: str) -> None:
        if not isinstance(message, str) or not message.strip():
            return
        self._execute(TALK_SCRIPT, spoken_text=message[:4000], timeout=65)

    def listen(self) -> str | None:
        transcript = self._execute(LISTEN_SCRIPT, timeout=35)
        return transcript[:4000] or None
