@echo off
REM Browser Gate Runner — credentials from 1Password via op run
REM
REM Requires: 1Password CLI (op) with OP_SERVICE_ACCOUNT_TOKEN set
REM Template: scripts\.env.beast.tpl references op://%UMH_OP_VAULT%/Cockpit Clerk
REM
REM Usage: run_browser_gate.bat [url] [passes]

setlocal enabledelayedexpansion

set "URL=%~1"
if "%URL%"=="" set "URL=https://universalmetaharness.tech/"

set "PASSES=%~2"
if "%PASSES%"=="" set "PASSES=3"

cd /d C:\dev\dev\OS
op run --env-file=scripts\.env.beast.tpl -- python scripts/browser_gate_collector.py --url "%URL%" --passes %PASSES% --output-json
