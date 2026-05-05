# Visible Browser Launch Backend v1

**Phase**: 94D.7
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Purpose

Opens a visible URL in the local default browser. This is NOT Playwright.
Does not scrape, control DOM, or read content. Only launches a URL.

## Module

`eos_ai/substrate/visible_browser_launch_backend.py`

## Backend Classification

`VISIBLE_BROWSER_LAUNCH` — not Playwright, not GUI_COMPUTER_USE.

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

## Execution Architecture

### WSL Interop Problem

WSL tmux sessions created via SSH lose the Windows interop socket.
Commands like `powershell.exe Start-Process` and `cmd.exe /c start`
fail with `UtilAcceptVsock:271: accept4 failed 110`.

Direct SSH commands DO have interop because `wsl -e bash` is invoked
by the Windows OpenSSH server which holds the socket.

### Solution: VPS-Delegated Execution

1. Worker validates approval and URL
2. Worker writes `pending_action_WO-*.json` to outbox
3. Worker polls inbox for `action_result_WO-*.json`
4. VPS reads pending_action via SSH
5. VPS executes `powershell.exe Start-Process <url>` via direct SSH
6. VPS writes action result to worker inbox via SSH stdin pipe

### Working Command

```bash
ssh ... 'wsl -e bash -c "powershell.exe Start-Process https://drive.google.com/"'
```

Returns exit code 0 when browser opens successfully.

## Key Functions

| Function | Purpose |
|----------|---------|
| `classify_backend()` | Returns "VISIBLE_BROWSER_LAUNCH" |
| `validate_url_allowed()` | Check URL against allowed/blocked domains |
| `build_open_url_command()` | Generate candidate launch commands |
| `build_drive_open_action()` | Full action payload for Drive |
| `execute_browser_launch()` | Execute launch (works in direct context) |
| `parse_launch_result()` | Human-readable status line |
