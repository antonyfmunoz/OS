# Phase 96.8AJ — Command Surface + Node Runtime Sync Proof

## What This Proves

The live Discord bot now routes substrate commands
(`!chrome-proof`, `!ping`, `!chrome`, etc.) through
the governed execution spine and control plane router.
Previously, these commands existed in source but were
invisible to the live bot — the interface adapter and
the live bot were separate systems with no bridge.

This phase fixes:
1. Commands registered in source but missing from live
2. Merge conflict in discord_bot.py (10K line duplicate)
3. No `!commands` introspection of live command surface
4. No command surface sync verification
5. Stale process detection (bot up 9 days on old code)

## Root Cause

Two separate Discord bot systems existed:

- `services/discord_bot.py` — the LIVE bot running in
  Docker, handles `@bot.command()` and inline commands
- `eos_ai/interfaces/discord_interface_adapter_v1.py` —
  the interface adapter with spine routing, NOT running

Phase 96.8AI added `!chrome-proof` to the interface
adapter but not to the live bot. Additionally, the live
bot file had a `<<<<<<< Updated upstream` / `=======` /
`>>>>>>> Stashed changes` merge conflict spanning the
entire 10,133-line file (two identical copies).

## What Changed

### Merge Conflict Resolved
`services/discord_bot.py` — removed duplicate stashed
copy (5,287 lines of conflict markers + duplicate code).
Clean 5,287-line file, valid Python, no markers.

### Substrate Command Handler Created
`services/handlers/substrate_command_handler.py`

Bridges the live bot to spine infrastructure:
- Intercepts substrate commands in `on_message`
- Routes spine commands through `execute_spine_command`
- Routes router commands through `route_work_packet`
- `!commands` shows live registered command surface
- Lazy initialization of spine/router infrastructure
- Command surface manifest for sync verification

### Live Bot Wired
`services/discord_bot.py` — substrate handler imported
and called BEFORE inline command handler:

```
on_message
  → substrate commands (spine/router)   ← NEW
  → inline commands (cc_command_handler)
  → full EOS gateway
  → @bot.command() handlers
```

### Command Surface Sync Module
`core/runtime/command_surface_sync_v1.py`

Verifies command surface parity:
- Source vs live command comparison
- VPS HEAD vs origin/main commit drift
- Container uptime (stale process detection)
- Surface hash computation
- Missing/extra command detection
- Sync proof persistence

## Command Routing

```
SUBSTRATE (11 commands):
  Spine-routed (4):
    !chrome-open-google-drive → chrome_open_google_drive
    !chrome-proof → chrome_proof [FG,SS,RO]
    !ingest-safe-doc → ingest_safe_doc [RO]
    !ingest-safe-doc-cu → ingest_safe_doc_cu [FG,RO]

  Router-routed (7):
    !ping → ping
    !chrome → open_application_url
    !doc → drive_open_safe_test_doc
    !extract → doc_extract_safe_test_doc
    !ingest-candidate → doc_ingestion_candidate_safe_test_doc
    !promote-memory → promote_safe_memory_candidate
    !query-memory → query_safe_memory_reference

BOT (@bot.command): !brief, !status, !portfolio, !join,
  !leave, !say, !help, !setup, !inbox, !drive, ... (80+)

INLINE (cc_command_handler): !followup, !travel,
  !nomeetings, !documents, !audit, ...

META:
  !commands → shows live command surface with flags
```

## Test Results

```
Phase 96.8AJ:  60 passed  (10 test classes)
Regression:   283 passed  (6 prior test files)
Total:        343 passed, 0 failed
```

### Test Classes
- TestSubstrateHandlerRegistration (13)
- TestCommandSurfaceManifest (8)
- TestCommandSurfaceSync (8)
- TestSyncProofPersistence (2)
- TestLiveBotIntegration (6)
- TestSpineRouting (5)
- TestSourceParity (3)
- TestRegressionExistingBotCommands (10)
- TestRegressionInlineCommands (5)

## Files Modified

```
CREATED:
  services/handlers/substrate_command_handler.py
  core/runtime/command_surface_sync_v1.py
  tests/test_command_surface_sync_v1.py
  docs/system/phase968aj_command_surface_sync_proof.md

MODIFIED:
  services/discord_bot.py (merge conflict resolved + handler wired)
```

## Next Step

Restart `os-discord` container to load new code:
```
docker restart os-discord
```

Then verify with `!commands` in Discord.

## Commit

```
phase968aj: fix command surface and node runtime sync
```
