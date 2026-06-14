# Phase 11 — Profile Runtime: Proof Document

**Date:** 2026-06-13
**Phase:** 11 — Profile Runtime
**Status:** COMPLETE

## What Was Built

Canonical runtime that separates and coordinates two orthogonal axes:
- **Profile Modes** — operator work identity (Engineer, Founder, Artist, Content, Research, Admin)
- **System Modes** — environmental/system states (Day, Night, AFK, Maintenance, Security, Focus, Emergency)

A user may have one profile mode active while multiple system modes run concurrently.

## Architecture Decisions

1. **Composition over creation**: Profile Runtime composes existing atoms from `substrate/workstation/` (ProfileMode, LifecycleMode, ProfileBehavior) and P8 Presence Runtime. Zero new execution engines.

2. **New enums instead of extending legacy**: Created `ProfileModeEnum` and `SystemModeEnum` with spec-required values rather than extending the legacy `ProfileMode`/`LifecycleMode` enums (which live in `substrate/workstation/` and have different value semantics like "developer" vs "engineer", "day_cycle" vs "day"). The legacy enums remain for backward compatibility.

3. **Deterministic state machines**: Both profile and system mode state machines are pure state — no LLM calls, no inference. Manual override always wins.

4. **Data-driven registries**: Both profiles and system modes load from JSON files, seed defaults on first run. Operators can modify without code changes.

5. **Exclusivity groups**: System modes use named exclusivity groups (e.g., "time_of_day") rather than hardcoded pair lists. Day and Night share the group — activating one deactivates the other automatically.

6. **Command Runtime integration**: Updated P9 Command Runtime to route profile switches through Profile Runtime (not Presence Runtime directly). Profile Runtime internally notifies Presence Runtime via `_notify_presence()`. Added `SWITCH_SYSTEM_MODE` action type with patterns for "activate focus mode", "go AFK", "turn on night mode", etc.

7. **No duplicated subsystem logic**: Profile Runtime does NOT duplicate attention logic (Presence owns it), workspace planning (Workstation owns it), or gap detection (Gap Engine owns it). It only reads from these subsystems and provides profile context.

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `substrate/organism/profile_runtime.py` | ~880 | Core runtime module |
| `tests/test_profile_runtime.py` | ~700 | 110 tests across 22 test classes |
| `data/proofs/2026-06-13_phase11_profile_runtime.md` | this file | Proof document |

## Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `transports/api/cockpit_operator_loop_routes.py` | +11 routes, +115 lines | Profile API endpoints |
| `cockpit/src/renderer/panels/ProfilePanel.tsx` | Replaced stub (16→~350 lines) | 6-tab cockpit panel |
| `cockpit/src/renderer/types/routes.ts` | visibility: stub→primary | Made profile panel visible |
| `substrate/canonical_types.py` | +24 type registrations | Phase 11 canonical types |
| `substrate/organism/command_runtime.py` | +SWITCH_SYSTEM_MODE, updated routing | System mode commands, profile → Profile Runtime |
| `tests/test_command_runtime.py` | Updated 5 tests | Match new routing destinations |

## Canonical Types Registered (24)

ProfileModeEnum, SystemModeEnum, ActivationSource, ProfileEventType, ConflictSeverity,
Profile, SystemMode, ProfileModeState, ProfileModeTransition, ProfilePreference,
ProfileContext, ProfileActivationPlan, ProfileRuntimeSnapshot, ProfileConflict,
ProfileRecommendation, ProfileRegistry, SystemModeRegistry, ProfileModeStateMachine,
SystemModeStateMachine, ConflictDetector, ProfileActivationPlanner, ProfileTimeline,
ProfileContextAssembler, ProfileRuntime

## API Routes (11)

- GET `/profile/state` — full runtime state
- GET `/profile/profiles` — all registered profiles
- GET `/profile/system-modes` — all registered system modes
- POST `/profile/activate-profile` — activate a profile mode
- POST `/profile/deactivate-profile` — deactivate current profile
- POST `/profile/activate-system-mode` — activate a system mode
- POST `/profile/deactivate-system-mode` — deactivate a system mode
- GET `/profile/activation-plan` — latest activation plan
- GET `/profile/conflicts` — detected conflicts
- GET `/profile/timeline` — chronological event timeline
- GET `/profile/context` — assembled profile context

## Tests Passing

- Profile Runtime: 110/110
- Command Runtime: 93/93 (5 updated for new routing)
- Workstation Runtime: 77/77
- Presence Runtime: 84/84
- **Total P8-P11: 364/364**

## Pre-Commit Gates

All 4 gates pass with zero violations:
- `check_dependency_direction.py` — PASS
- `check_instance_leak.py` — PASS
- `check_projection_leak.py` — PASS
- `check_type_divergence.py` — PASS

## Acceptance Results

| # | Requirement | Status |
|---|-------------|--------|
| 1 | Profile Registry (6 profiles, data-driven JSON) | PASS |
| 2 | System Mode Registry (7 modes, data-driven JSON) | PASS |
| 3 | Profile Mode State Machine (activate, deactivate, override) | PASS |
| 4 | System Mode State Machine (concurrent modes, exclusivity) | PASS |
| 5 | Profile Activation Plan (planning only, status=planned) | PASS |
| 6 | Workstation Runtime consumes profile context | PASS (domain_weights) |
| 7 | Presence Runtime consumes profile (via _notify_presence) | PASS |
| 8 | Tick/Gap/Projection weighting via domain_weights | PASS |
| 9 | Command Runtime routes profile + system mode commands | PASS |
| 10 | Profile Timeline (chronological events) | PASS |
| 11 | Conflict Detection (exclusivity, unsafe combos, risk) | PASS |
| 12 | Cockpit Panel (6 tabs, full interactivity) | PASS |
| 13 | APIs (11 routes) | PASS |
| 14 | No execution occurs (all plans status=planned) | PASS |

## Limitations

- Profile Runtime does not yet consume Workstation Runtime's `prepare_workspace()` — that integration flows the other direction (Workstation queries Profile for template preference).
- System mode effects are declarative (stored as JSON) but not yet consumed by Gap/Projection/Tick engines at runtime — they read `domain_weights` but don't yet check `effects.risk_ceiling`.
- Legacy `substrate/workstation/profile_modes.py` and `lifecycle_modes.py` still exist with their original values. Phase 11 creates parallel enums with spec-aligned values rather than modifying legacy code that may be consumed elsewhere.

## Next Phase Recommendation

**Session Runtime** — manage coding sessions as first-class entities with:
- Session lifecycle (create, focus, pause, resume, close)
- Session ↔ Profile binding (a session inherits the active profile's context)
- Session ↔ WorkPacket binding (a session tracks which packets it's executing)
- Session handoff (Beast ↔ VPS with state preservation)
- Session timeline and audit trail
