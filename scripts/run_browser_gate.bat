@echo off
REM Browser Gate Runner — reads credentials from %USERPROFILE%\.umh\cockpit.env
REM
REM Create %USERPROFILE%\.umh\cockpit.env with:
REM   UMH_COCKPIT_EMAIL=your@email.com
REM   UMH_COCKPIT_PASSWORD=your-password
REM
REM Usage: run_browser_gate.bat [url] [passes]

setlocal enabledelayedexpansion

set "URL=%~1"
if "%URL%"=="" set "URL=https://universalmetaharness.tech/"

set "PASSES=%~2"
if "%PASSES%"=="" set "PASSES=3"

set "ENV_FILE=%USERPROFILE%\.umh\cockpit.env"

if not exist "%ENV_FILE%" (
    echo ERROR: %ENV_FILE% not found
    echo Create it with UMH_COCKPIT_EMAIL and UMH_COCKPIT_PASSWORD
    exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
    set "%%A=%%B"
)

cd /d C:\dev\dev\OS
python scripts/browser_gate_collector.py --url "%URL%" --passes %PASSES% --output-json
