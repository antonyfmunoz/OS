# Start Kokoro TTS Server on Beast
# Run as: powershell -ExecutionPolicy Bypass -File E:\kokoro-tts\start_kokoro.ps1
# Or register as a scheduled task for auto-start on boot

$ErrorActionPreference = "Stop"

$venvPython = "E:\kokoro-tts\venv\Scripts\python.exe"
$serverScript = "E:\kokoro-tts\kokoro_server.py"
$logFile = "E:\kokoro-tts\kokoro.log"

if (-not (Test-Path $venvPython)) {
    Write-Error "Python venv not found at $venvPython"
    exit 1
}

if (-not (Test-Path $serverScript)) {
    Write-Error "Server script not found at $serverScript"
    exit 1
}

Write-Host "Starting Kokoro TTS server..."
Write-Host "  Python: $venvPython"
Write-Host "  Script: $serverScript"
Write-Host "  Log:    $logFile"
Write-Host "  Port:   8880"

& $venvPython $serverScript *>&1 | Tee-Object -FilePath $logFile
