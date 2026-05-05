@echo off
REM workstation_daemon.bat — Launch the supervised station daemon on Windows.
REM
REM Usage:
REM   scripts\workstation_daemon.bat
REM   scripts\workstation_daemon.bat founder_workstation
REM
REM Auto-start on login (Windows Task Scheduler):
REM   1. Open Task Scheduler
REM   2. Create Basic Task → "EOS Workstation Daemon"
REM   3. Trigger: "When I log on"
REM   4. Action: Start a program
REM      Program: C:\path\to\OS\scripts\workstation_daemon.bat
REM      Arguments: founder_workstation
REM      Start in: C:\path\to\OS
REM   5. Check "Run with highest privileges"
REM   6. Under Conditions: Uncheck "Start only if on AC power"

cd /d "%~dp0\.."

set NODE_ID=antony-workstation
set PROFILE=%1

if "%PROFILE%"=="" (
    echo [workstation_daemon.bat] starting supervised daemon node=%NODE_ID%
    python -m eos_ai.substrate.daemon_supervisor --node-id %NODE_ID%
) else (
    echo [workstation_daemon.bat] starting supervised daemon node=%NODE_ID% profile=%PROFILE%
    python -m eos_ai.substrate.daemon_supervisor --node-id %NODE_ID% --profile %PROFILE%
)
