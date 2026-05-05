# Chrome Visible Browser Launch Backend v1

**Phase**: 94D.7R
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Purpose

Opens a visible URL in Google Chrome specifically on the local machine.
This is NOT Playwright. This does NOT scrape, control DOM, or read content.
It only launches a URL visibly in Chrome.

## Module

`eos_ai/substrate/visible_browser_launch_backend.py`

## Backend Classification

`VISIBLE_CHROME_LAUNCH` — not Playwright, not GUI_COMPUTER_USE, not Explorer/default handler.

## Chrome Detection

The backend checks three standard Windows paths for chrome.exe:

1. `C:\Program Files\Google\Chrome\Application\chrome.exe`
2. `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
3. `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe`

Uses PowerShell `Test-Path` to find the first existing path.

## Allowed Domains

- `drive.google.com`

## Blocked Domains

- `mail.google.com`
- `accounts.google.com`
- `calendar.google.com`
- `contacts.google.com`
- `photos.google.com`
- `youtube.com`
- `www.youtube.com`

## Launch Command

```powershell
powershell.exe -NoProfile -Command "
  $chromeCandidates = @(
    '$env:ProgramFiles\Google\Chrome\Application\chrome.exe',
    '${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe',
    '$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe'
  );
  $chrome = $chromeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1;
  if (-not $chrome) { Write-Output 'CHROME_NOT_FOUND'; exit 1 };
  Start-Process -FilePath $chrome -ArgumentList 'https://drive.google.com/';
  Write-Output $chrome
"
```

## If Chrome Is Not Found

- Does NOT silently fall back to Explorer or default browser
- Emits `BACKEND_MISSING` / `CHROME_NOT_FOUND`
- Asks advisor for decision:
  - A: Locate Chrome manually
  - B: Approve default browser fallback
  - C: Approve Edge fallback
  - D: Approve Playwright fallback
  - E: Cancel test

## Execution Architecture (VPS-Delegated)

Same as Phase 94D.7: WSL tmux sessions lack Windows interop.
Worker writes `pending_action` with `chrome_command` field.
VPS executes via direct SSH (which has interop).
VPS writes result back to inbox.

### Working SSH Command (from VPS)

```bash
ssh ... 'powershell.exe -NoProfile -Command "..."'
```

Note: Execute PowerShell directly via SSH to Windows, NOT through WSL wrapper.
The WSL wrapper loses quoting context for PowerShell commands.

## Key Functions

| Function | Purpose |
|----------|---------|
| `classify_backend()` | Returns "VISIBLE_CHROME_LAUNCH" |
| `find_chrome_candidates()` | Return Windows path list |
| `build_chrome_detection_command()` | PowerShell script to find Chrome |
| `build_open_url_in_chrome_command(url)` | Full PowerShell launch command |
| `validate_url_allowed(url)` | Check URL against allowed/blocked |
| `build_drive_open_action()` | Full action payload |
| `build_backend_missing_message(reason)` | BACKEND_MISSING message |
| `execute_chrome_launch(url)` | Execute Chrome launch locally |
| `parse_launch_result(result)` | Human-readable status |

## Confirmed Chrome Path (Phase 94D.7R Test)

```
C:\Program Files\Google\Chrome\Application\chrome.exe
```
