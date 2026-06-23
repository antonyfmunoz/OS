# Campaign 20 — Voice Operations: Complete

**Status:** MERGED to main
**PR:** #68 (merged)
**Date:** 2026-06-18
**Commits:** 3 (feat + route fix + logging fix)

---

## What Was Built

Campaign 20 implements the **unified voice brain** — a composition layer that unifies three existing voice pipelines (ingress, session, output) under a single operational runtime.

### 5 Runtimes (substrate/workstation/)

| Runtime | File | Lines | Purpose |
|---------|------|-------|---------|
| C20.0 | `voice_ingress_runtime.py` | 352 | Classify raw audio events by source type and activation mode |
| C20.1 | `voice_session_manager.py` | 367 | Manage voice session lifecycle (create, join, leave, end) |
| C20.2 | `ambient_wake_runtime.py` | 407 | Always-on state machine: dormant → listening → triggered → processing |
| C20.3 | `voice_output_runtime.py` | 265 | Route output to appropriate TTS/audio channel |
| C20.4 | `voice_operations_runtime.py` | 462 | Unified facade composing all 4 sub-runtimes + VoiceQueryEngine |

### 5 Route Files (transports/api/)

- `cockpit_voice_ingress_routes.py` — ingress classification + stats
- `cockpit_voice_session_routes.py` — session CRUD + listing
- `cockpit_ambient_wake_routes.py` — wake state + device management
- `cockpit_voice_output_routes.py` — output routing + snapshot
- `cockpit_voice_ops_routes.py` — unified operations snapshot + health

All mounted in `cockpit.py` as FastAPI routers.

### 6 Test Files — 207 Tests (all passing)

- `test_c20_0_voice_ingress.py` (351 lines)
- `test_c20_1_voice_session_manager.py` (375 lines)
- `test_c20_2_ambient_wake.py` (236 lines)
- `test_c20_3_voice_output.py` (183 lines)
- `test_c20_4_voice_operations.py` (461 lines)
- `test_c20_integration.py` (434 lines) — 6 acceptance tests

### Types Registered

38 new types added to `substrate/canonical_types.py` — all voice-related enums and models.

## Architecture

```
VoiceOperationsRuntime (C20.4 — facade)
  ├── VoiceIngressRuntime (C20.0) — classify events
  ├── VoiceSessionManager (C20.1) — session lifecycle
  ├── AmbientWakeRuntime (C20.2) — always-on state machine
  ├── VoiceOutputRuntime (C20.3) — output routing
  └── VoiceQueryEngine (Phase 35) — context-grounded queries
```

All sub-runtimes use lazy accessors with graceful degradation — if any component is unavailable, the facade continues operating with reduced capability.

## CodeRabbit Review Fix

Fixed 7 bare `except Exception:` blocks that were missing `logger.debug()` calls across `voice_ingress_runtime.py` and `voice_operations_runtime.py`. All 15 exception handlers now log at debug level.

## Totals

- **18 files** changed
- **4,246 lines** added
- **207 tests** — all passing
- **38 types** registered
- **0 bare excepts** remaining
