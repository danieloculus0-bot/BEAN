# Upgrade BEAN's local conversational model without replacing its reasoning backend.
# Run from PowerShell: .\scripts\bean_upgrade_chat.ps1
param(
    [string]$Model = "gemma3:4b"
)
$ErrorActionPreference = 'Stop'
$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCommand) {
    $ollamaExe = $ollamaCommand.Source
} elseif (Test-Path 'D:\Ollama\app\ollama.exe') {
    $ollamaExe = 'D:\Ollama\app\ollama.exe'
} else {
    throw "Ollama is not on PATH or D:\Ollama\app\ollama.exe. Install or locate Ollama first."
}
Write-Host "Installing BEAN chat model: $Model"
& $ollamaExe pull $Model
if ($LASTEXITCODE -ne 0) {
    throw "Ollama model download failed. BEAN's existing models remain available."
}
# Applies to future launches of the desktop application and python -m bean.voice.
[Environment]::SetEnvironmentVariable("BEAN_CHAT_MODEL", $Model, "User")
$env:BEAN_CHAT_MODEL = $Model
Write-Host "BEAN_CHAT_MODEL set to $Model for future sessions."
Write-Host "Restart BEAN to use the new model. Keep the coding/reasoning model installed."
& $ollamaExe list
