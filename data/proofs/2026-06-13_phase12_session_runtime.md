# Phase 12: Session Runtime — Proof Document

**Date:** 2026-06-13
**Phase:** 12
**Status:** COMPLETE

## What Was Built

Session Runtime — makes Session a first-class runtime entity so UMH understands
WHERE the operator is operating (complementing Profile Runtime's WHO and
Presence Runtime's HOW AVAILABLE).

## Architecture

### Core Module: `substrate/organism/session_runtime.py` (1,114 lines)

**Enums (5):**
- `SessionType` — 10 session types (desktop, laptop, phone, tablet, vps, server, container, browser, remote-desktop, agent-session)
- `SessionStatus` — 5 statuses (active, background, idle, suspended, disconnected) with `is_alive` property
- `SessionAuthority` — 3 authority levels (primary, secondary, background)
- `SessionEventType` — 12 lifecycle event types
- `HandoffStatus` — 3 handoff states (pending, completed, expired)

**Data Models (6):**
- `Session` — canonical session with all spec fields + `bound_work_packets` and `metadata`
- `SessionEvent` — lifecycle event with auto-generated `sevt-*` IDs
- `SessionHandoff` — handoff package with operational context snapshots
- `SessionContinuityLink` — Profile → Session → Objective → WorkPacket → Outcome lineage
- `SessionRuntimeSnapshot` — complete state capture with authority hierarchy

**Engines (5):**
- `SessionRegistry` — state management, authority classification, work packet binding, persistence
- `SessionLifecycleEngine` — lifecycle transitions, timeout detection (5min idle, 10min disconnect)
- `SessionHandoffRuntime` — handoff assembly from P6/P7/P10/P11 snapshots
- `SessionContinuityGraph` — JSONL-persisted lineage tracking
- `SessionTimeline` — chronological event recording

**Top-level:**
- `SessionRuntime` — orchestrator composing all engines, emitting timeline events, notifying presence
- `get_session_runtime()` / `reset_session_runtime()` — singleton

### API Routes: 13 routes under `/session/`

GET: `/session/state`, `/session/list`, `/session/active`, `/session/history`, `/session/timeline`
POST: `/session/start`, `/session/suspend`, `/session/resume`, `/session/disconnect`, `/session/restore`, `/session/promote`, `/session/handoff`, `/session/handoff/complete`

### Cockpit Panel: `SessionPanel.tsx` (417 lines)

5 tabs: Active, Timeline, Handoffs, Devices, History
- Active: primary session (highlighted), secondary/background sessions with Promote/Resume/Restore actions
- Timeline: reverse-chronological lifecycle events
- Handoffs: handoff history with completion actions
- Devices: sessions grouped by device
- History: suspended/disconnected sessions

KPI row: Primary, Active count, Total count, Handoffs count
Auto-refresh: 15 seconds

### Canonical Types: 16 registered in `canonical_types.py`

### Command Runtime Integration

- `SWITCH_SESSION` routes to `session_runtime` (was `presence_runtime`)

## Design Decisions

1. **Authority model uses promote/demote, not set.** At most one primary session at any time.
   Promoting a session automatically demotes the current primary. Eliminates multiple-primary bugs.

2. **Handoff assembles snapshots, not transfers state.** The handoff package captures operational
   context from P6/P7/P10/P11 at handoff time. The receiving session reads the snapshot.
   Correct for cross-device scenarios with intermittent connectivity.

3. **Session types are more granular than device types.** `device_registry.json` has 4 devices;
   `SessionType` has 10 types including container, browser, agent-session. A single device
   can host multiple session types (desktop + container + agent-session on VPS).

4. **Lifecycle engine enforces state machine rules.** `resume_session` only works on suspended/idle.
   `restore_session` only works on disconnected. Prevents invalid state transitions.

5. **Continuity graph preserves full lineage.** Every work packet binding and profile association
   creates a link in the graph. Any work can be traced: Profile → Session → WorkPacket.

## Cross-Runtime Integration

| Phase | Integration Point |
|-------|-------------------|
| P5 Tick Loop | `check_timeouts()` called by tick loop for idle/disconnect detection |
| P6 Projection Engine | Projection snapshot included in handoff packages |
| P7 Continuity Runtime | Continuity snapshot included in handoff packages |
| P8 Presence Runtime | Session start notifies presence; session registration |
| P9 Command Runtime | `switch_session` routes to session_runtime |
| P10 Workstation Runtime | Workstation state included in handoff packages |
| P11 Profile Runtime | Profile context included in handoff packages; profile-session binding |

## Test Results

- **90 tests** in `tests/test_session_runtime.py`
  - 5 enum test classes
  - 6 data model test classes
  - 16 registry tests
  - 8 lifecycle engine tests
  - 6 handoff runtime tests
  - 5 continuity graph tests
  - 4 timeline tests
  - 22 session runtime integration tests
  - 2 singleton tests
  - 11 acceptance tests
- **93 command runtime tests** updated — all pass
- **523/523 combined P7-P12 tests** pass

## Acceptance Scenario Verification

```
Engineer Profile active → PASS (profile_id binding)
Desktop session starts → PASS (session_type="desktop")
Desktop becomes primary → PASS (authority="primary")
Workstation Runtime prepares Engineering Workspace → PASS (workspace integration via handoff)
WorkPackets attach to Desktop Session → PASS (bind_work_packet)
Operator leaves → PASS (suspend_session)
Phone session becomes active → PASS (start_session phone, promote_to_primary)
Continuity handoff generated → PASS (initiate_handoff captures snapshots)
Operator returns to Desktop → PASS (resume_session)
Session restored → PASS (promote_to_primary on desktop)
Work continues without context loss → PASS (timeline preserves full history)
Full lifecycle persisted → PASS (timeline contains all event types)
```

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `substrate/organism/session_runtime.py` | NEW | 1,114 |
| `tests/test_session_runtime.py` | NEW | 1,012 |
| `cockpit/src/renderer/panels/SessionPanel.tsx` | NEW | 417 |
| `transports/api/cockpit_operator_loop_routes.py` | MODIFIED | +223 |
| `cockpit/src/renderer/stores/cockpitStore.ts` | MODIFIED | +1 |
| `cockpit/src/renderer/types/routes.ts` | MODIFIED | +2 |
| `cockpit/src/renderer/components/Shell.tsx` | MODIFIED | +2 |
| `substrate/canonical_types.py` | MODIFIED | +17 |
| `substrate/organism/command_runtime.py` | MODIFIED | +1 |
| `tests/test_command_runtime.py` | MODIFIED | +2 |

## Future: Phase 13 Candidates

1. **Governance Runtime** — unified governance policy engine across all subsystems
2. **Notification Runtime** — cross-device notification routing with priority/interruption
3. **Execution Coordinator** — tie sessions to live execution with progress tracking
4. **Multi-Operator Support** — extend session model for team-based operation
