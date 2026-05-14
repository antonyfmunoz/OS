# Phase 96.8H.1 — Windows Relay Client Path Unification

**Date:** 2026-05-06
**Status:** COMPLETE
**Gate:** COMMIT_AND_PUSH_PHASE_968H1

---

## Why This Phase Exists

Phase 96.8H built the Windows Interactive Desktop Adapter v1 with relay
client, but used `eos_relay` as the relay root directory name. Manual
testing proved the relay was healthy and responding at the canonical path
`eos_advisor_messages/windows_desktop_relay`. The mismatch meant the WSL
relay client wrote packets to a path the Windows relay was not watching.

Phase 96.8H.1 unifies all relay path defaults to the canonical root that
was already proven working in the live environment.

---

## Canonical Relay Root

| Environment | Path |
|-------------|------|
| Windows | `%USERPROFILE%\eos_advisor_messages\windows_desktop_relay` |
| WSL | `/mnt/c/Users/<username>/eos_advisor_messages/windows_desktop_relay` |
| VPS/Linux | `Path.home()/eos_advisor_messages/windows_desktop_relay` (fallback, not a relay environment) |

---

## Changes Made

### eos_ai/substrate/windows_desktop_relay_client.py

| Change | Detail |
|--------|--------|
| `RELAY_DIR_NAME` | `os.path.join("eos_advisor_messages", "windows_desktop_relay")` |
| `_resolve_windows_home()` | Detects WSL via `/mnt/c`, resolves Windows user home via `cmd.exe /C echo %USERPROFILE%`, falls back to scanning `/mnt/c/Users/` |
| `_default_relay_root()` | Environment-aware: WSL → Windows-mounted path, native Windows → `Path.home()`, VPS → `Path.home()` fallback |
| `_is_windows_relay_environment()` | Returns True on native Windows or WSL with `/mnt/c`, False on VPS |
| `resolve_relay_paths(relay_root)` | Explicit override via `--relay-root` CLI flag |
| CLI `_cli_main()` | `--action PING|CHECK`, `--relay-root`, `--dry-run`, `--timeout`, `--debug` |

### scripts/windows_interactive_desktop_relay.ps1

| Change | Detail |
|--------|--------|
| `$InboxPath` default | `$HOME\eos_advisor_messages\windows_desktop_relay\inbox` |
| `$OutboxPath` default | `$HOME\eos_advisor_messages\windows_desktop_relay\outbox` |

### tests/test_windows_desktop_relay_client.py

| Tests Added | Purpose |
|-------------|---------|
| `TestRelayDirNameCanonical` | RELAY_DIR_NAME matches canonical path |
| `TestResolveWindowsHome` | Returns None without /mnt/c |
| `TestDefaultRelayRoot` (3 tests) | WSL uses Windows home, VPS uses Path.home(), Windows native uses Path.home() |
| `TestIsWindowsRelayEnvironment` (2 tests) | True on Windows/WSL, False on VPS |
| `TestResolveRelayPaths` (4 tests) | Explicit override, None uses default, request written to inbox, result read from outbox |
| `TestCLIDebugOutput` | CLI --debug prints relay_root, inbox, outbox paths |
| `TestSendAndWaitDryRun.test_ping_dry_run_no_gui_action` | PING dry-run performs no GUI action |

---

## Tests Passed

| Test File | Tests | Status |
|-----------|-------|--------|
| test_windows_desktop_relay_client.py | 24 | ALL PASS |

---

## Architectural Doctrine

### Environment Detection

The relay client detects its environment at import time:

1. **Native Windows** (`os.name == "nt"`): Use `Path.home()` directly
2. **WSL** (`/mnt/c` exists): Resolve Windows user home, construct mounted path
3. **VPS/Linux** (no `/mnt/c`): Fall back to `Path.home()` — not a relay environment

### Fail-Closed Behavior

`_is_windows_relay_environment()` returns False on VPS/Linux. The local worker
auto-loop uses this to gate relay routing — packets requiring the Windows
Desktop Adapter will not be routed on a machine that cannot reach the relay.

### Explicit Override

The `--relay-root` CLI flag and `resolve_relay_paths(relay_root)` API allow
explicit path override for testing, non-standard installations, or future
multi-user scenarios.

---

## What Was Not Executed

| Item | Status |
|------|--------|
| W0-001 CU executed | NO |
| Chrome opened | NO |
| Drive/Docs accessed | NO |
| Gmail accessed | NO |
| Secrets captured | NO |
| GUI actions performed | NO |
| Memory promoted | NO |
| Windows relay started | NO |

---

## Status

| Item | Status |
|------|--------|
| Memory promoted | NO |
| Committed | YES |
| Pushed | YES |
| W0-001 CU executed | NO |
| Drive/Docs accessed | NO |
| Secrets captured | NO |
