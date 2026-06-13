# Phase 8: Presence Runtime — Proof of Completion

**Date:** 2026-06-13
**Author:** Developer Agent (Claude Opus 4.6)
**Status:** COMPLETE

## What Was Built

The Presence Runtime makes the operator a first-class entity in UMH. The system
now understands where the operator is, which device/session is active, what
attention state applies, and whether to interrupt.

## Components

### Core Engine (`substrate/organism/presence_runtime.py` — 973 lines)

**Enums:**
- `PresenceAttentionState` — FOCUSED/AVAILABLE/AWAY/OFFLINE/SLEEPING with `.is_present`/`.is_absent`
- `InterruptionLevel` — CRITICAL_ONLY/NORMAL/QUEUE/DEFER
- `PresenceEventType` — 10 canonical event types
- `InteractionSurface` — 8 operator interaction surfaces

**Data Models:**
- `DeviceInfo` — enriched device record (static registry + live presence)
- `SessionInfo` — first-class session with host/profile/status/surface tracking
- `PresenceSnapshot` — 14-field canonical presence state
- `PresenceEvent` — timeline event with type/summary/details

**Engines:**
- `DeviceRegistry` — loads from infra/device_registry.json, merges with live sessions
- `SessionRegistry` — multi-session support with lifecycle, history, and primary selection
- `AttentionEngine` — 5-state deterministic machine (60s focused, 300s away, 21600s sleeping)
- `InterruptibilityEngine` — deterministic state→level mapping, recommendation filtering
- `PresenceTimeline` — JSONL-backed event chronology
- `PresenceRuntime` — top-level orchestrator composing all engines

**Singleton:** `get_presence_runtime()` / `reset_presence_runtime()`

### API Routes (14 endpoints in cockpit_operator_loop_routes.py)

- GET `/presence/status` — current presence state
- GET `/presence/snapshot` — last captured snapshot
- POST `/presence/capture` — capture new snapshot
- GET `/presence/devices` — all registered devices
- GET `/presence/sessions` — active sessions
- POST `/presence/session/register` — register new session
- POST `/presence/session/end` — end session
- POST `/presence/session/heartbeat` — session heartbeat
- POST `/presence/interaction` — record operator interaction
- POST `/presence/profile` — change profile mode
- GET `/presence/attention` — current attention state
- GET `/presence/interruption` — interruptibility query
- GET `/presence/timeline` — presence event history
- GET `/presence/history` — session history

### Cockpit Panel (`cockpit/src/renderer/panels/PresencePanel.tsx`)

5-tab panel: Overview, Devices, Sessions, Attention, History
- Overview: KPI cards (status, attention, sessions, snapshots) + current state grid
- Devices: device list with online indicators and session counts
- Sessions: active sessions with metadata
- Attention: large state display + interruptibility rule matrix + integration filters
- History: chronological event timeline with color-coded badges

### Type Registration

15 types registered in `substrate/canonical_types.py` under "Phase 8: Presence Runtime"

## Integration Hooks

- `get_continuity_presence_input()` → feeds into Phase 7 ContinuityRuntime
- `get_tick_loop_filter()` → feeds into Phase 5 StrategicTickLoop (suppress/normal/accumulate/defer)
- `get_projection_context()` → feeds into Phase 6 ProjectionEngine

## Interruptibility Rules

| Attention State | Interruption Level | Normal Alerts | Critical Alerts | Recommendations |
|---|---|---|---|---|
| FOCUSED | CRITICAL_ONLY | Block | Pass | Suppress |
| AVAILABLE | NORMAL | Pass | Pass | Normal |
| AWAY | QUEUE | Block | Block | Accumulate |
| OFFLINE | DEFER | Block | Block | Defer |
| SLEEPING | DEFER | Block | Block | Defer |

## Test Results

**Phase 8:** 84/84 passing (0.24s)
- 4 enum test classes
- 5 data model test classes
- 8 session registry tests
- 9 attention engine tests
- 10 interruptibility engine tests
- 6 timeline tests
- 2 device registry tests
- 18 presence runtime tests
- 2 singleton tests
- 4 integration hook tests
- 9 acceptance tests (device registration, multi-session, presence transitions,
  attention transitions, event emission, continuity integration,
  interruptibility rules, full lifecycle, governance boundary)

**Regression (Phases 4-7):** 198/198 passing (1.52s)
**Total:** 282/282 passing

## Deployment

- os-operator: `docker restart os-operator` — clean startup
- Cockpit: `bash cockpit/deploy.sh` — deployed to umh-cockpit.fly.dev

## Architecture Compliance

- All code in `substrate/organism/` — correct layer
- No imports from transports/ or services/ in substrate
- No LLMs in core path — fully deterministic
- No duplicated types — all registered in canonical_types.py
- No instance context leaks — device registry loaded from file, not hardcoded
- Composes existing primitives without modifying them
- Governance boundary maintained: observe/classify/recommend only
