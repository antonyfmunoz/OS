# Phase 96.8AK — Live Runtime Identity and Git Parity Proof

## What This Proves

The live Discord bot now:
1. Reports its own runtime identity (`!version`, `!runtime`)
2. Exposes its full command surface (`!commands`)
3. Detects and blocks stale runtimes (VPS != origin/main)
4. Routes substrate commands (`!chrome-proof`, `!ping`, etc.)
   through the governed spine BEFORE orchestration ingress
5. Logs a full diagnostic banner on startup

## Root Cause (from Phase 96.8AJ)

The substrate command intercept was placed at line 2338 in
`services/discord_bot.py` — AFTER the orchestration ingress
(line 1767) and CC injection (line 1826), both of which
accepted all messages and returned early. Substrate commands
never reached their handler.

## The Fix

Moved substrate intercept from line 2338 to line 1765:
- AFTER archive (line 1763) — archive records message history
- BEFORE orchestration ingress (line 1770) — general routing
- BEFORE CC injection (line 1834) — tmux session routing

This ensures `!chrome-proof` and other substrate commands
are caught and spine-routed before any general handler can
steal the message.

## on_message Dispatch Chain (corrected)

```
on_message
  → buffer / day-ritual / onboarding / archive
  → SUBSTRATE COMMANDS (spine/router)    ← FIXED (was at end)
  → orchestration ingress
  → CC injection (tmux session)
  → PseudoLive fallback
  → multi-part assembly
  → inline commands
  → full EOS gateway
  → @bot.command() handlers
```

## Live Startup Banner

```
[03:39:01] [substrate-handler] ==================================================
[03:39:01] [substrate-handler] Substrate Command Handler — ACTIVE
[03:39:01] [substrate-handler] VPS HEAD: 7657bd4d
[03:39:01] [substrate-handler] origin/main: 7657bd4d
[03:39:01] [substrate-handler] parity: SYNCED
[03:39:01] [substrate-handler] substrate commands: 11
[03:39:01] [substrate-handler] meta commands: 3
[03:39:01] [substrate-handler] surface hash: fbce7519491c
[03:39:01] [substrate-handler] PID: 1
[03:39:01] [substrate-handler] commands: !chrome, !chrome-open-google-drive,
    !chrome-proof, !doc, !extract, !ingest-candidate, !ingest-safe-doc,
    !ingest-safe-doc-cu, !ping, !promote-memory, !query-memory
[03:39:01] [substrate-handler] ==================================================
```

## Meta Commands Added

| Command    | Response                                    |
|------------|---------------------------------------------|
| `!version` | VPS HEAD, origin/main, parity, hashes       |
| `!runtime` | PID, boot time, uptime, hostname, container |
| `!commands`| Full command surface with flags and routing  |

## Stale Runtime Detection

When VPS HEAD != origin/main, all substrate commands are
blocked with a remediation message:

```
**!ping** -- STALE_RUNTIME
VPS HEAD: `abc1234` != origin/main: `def5678`
Run `git pull` on VPS then `docker restart os-discord`
```

## Test Results

```
Phase 96.8AK:  28 passed  (8 test classes)
Phase 96.8AJ:  60 passed  (9 test classes, regression)
Total:         88 passed, 0 failed
```

### Phase 96.8AK Test Classes
- TestStaleRuntimeDetection (4) — stale/not-stale/unknown/blocks
- TestMetaCommands (7) — !version/!runtime/!commands recognition + response
- TestSubstrateInterceptOrder (3) — before orch, before CC, after archive
- TestCommandRegistryParity (5) — hash determinism, chrome-proof present
- TestLogStartup (2) — banner output + parity line
- TestBotWiringIntegrity (5) — import, call, no conflicts, compiles
- TestContainerIdentity (3) — container ID, boot time, PID

## Files Modified

```
MODIFIED:
  services/discord_bot.py
    — moved substrate intercept from line 2338 to line 1765
    — added log_startup import and call in on_ready

  services/handlers/substrate_command_handler.py
    — added !version, !runtime meta commands
    — added stale runtime detection (_is_stale_runtime)
    — added boot metadata (_BOOT_TIME, _BOOT_PID)
    — added container identity (_container_id)
    — added origin commit hash, router contract hash, file hash
    — added log_startup() diagnostic banner

CREATED:
  tests/test_live_runtime_identity_v1.py (28 tests)
  docs/system/phase968ak_live_runtime_identity_proof.md
```

## Commit

```
phase968ak: prove live runtime identity and git parity
```
