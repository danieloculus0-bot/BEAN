# From Windows PowerShell: .\scripts\bean_talk.ps1
# Uses whatever Ollama chat model is already installed locally.
$ErrorActionPreference = 'Stop'
Push-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
try {
    python -m bean.voice --talk @args
} finally {
    Pop-Location
}
