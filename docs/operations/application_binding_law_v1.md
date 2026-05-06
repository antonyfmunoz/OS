# Application Binding Law v1

**Phase:** 96.8F
**Status:** Active
**Layer:** UMH Substrate — Adapter Boundary Layer
**Module:** `core/environment_bridge/execution_binding_contracts.py`

## Law

If a work packet specifies an application (e.g., Chrome), the system
must launch that exact application via the declared launch method.
Generic OS shell routing is disallowed for application-bound actions
unless the application contract explicitly permits it.

## Disallowed Launch Methods for Chrome

| Method | Allowed? | Why |
|--------|----------|-----|
| `direct_executable` | YES | Governed, deterministic, auditable |
| `explorer_url` | NO | Delegates to OS default handler — ungoverned |
| `default_browser` | NO | Not deterministic — could open Edge, Firefox |
| `shell_url_open` | NO | Generic OS shell open — ungoverned |
| `generic_start_url` | NO | PowerShell Start-Process without exe path |
| `unknown_browser` | NO | Unknown application identity |

## The Chrome vs Explorer Problem

Phase 96.8D observed that when the system was told to "open Chrome,"
WSL/tmux execution could route through:

1. `explorer.exe <url>` — opens in whatever Windows considers default
2. `start <url>` — same as explorer
3. `xdg-open` or `wslview` — Linux-side URL handler → Windows default
4. `powershell -c Start-Process <url>` — without specifying Chrome exe

All of these bypass the application binding. The founder wanted Chrome
specifically, but the system didn't enforce that Chrome was the thing
that actually opened.

## Correct Pattern

```
application_id: google_chrome_windows
launch_method: direct_executable
executable_path: C:\Program Files\Google\Chrome\Application\chrome.exe
wsl_executable_path: /mnt/c/Program Files/Google/Chrome/Application/chrome.exe
disallowed_launch_methods:
  - explorer_url
  - default_browser
  - shell_url_open
  - generic_start_url
  - unknown_browser
```

The validator rejects any execution binding where the launch_method
is in the disallowed list. This is enforced at packet validation time,
before any execution begins.

## Scope

This law applies to all application-bound actions, not just Chrome.
Any future application binding (e.g., VS Code, Excel) must declare
its own allowed/disallowed launch methods.
