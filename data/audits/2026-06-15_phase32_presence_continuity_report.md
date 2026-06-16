# Phase 32 — Presence & Continuity Runtime

**Date:** 2026-06-15
**Status:** COMPLETE
**Tests:** 108/108 passing
**Lines:** ~1,850 new across 8 files, ~30 modified in 3 files

---

## What It Does

Phase 32 creates the operator presence and continuity layer — the first
system that models the operator rather than the organism. UMH can now answer:

- What am I doing?
- What was I doing?
- What should I resume?
- What device am I on?
- What workspace is active?
- What session should continue?

Across VPS, Windows, iPad, and iPhone.

---

## Architecture

### ContinuityEngine (aggregation façade)

Composes:
- **WorkspaceObservationEngine** → current workspace/session
- **WorkspaceTopologyEngine** → runtime context
- **ActionBridge** → (reserved, no active queue API)
- **OperatorContextEngine** → pending approvals, health status
- **UMHNodeRegistry** → node identification

All dependencies lazy-loaded with try/except for graceful degradation.
Same façade pattern as OperatorContextEngine (Phase 31).

### Presence Detection (deterministic)

| Signal | Method | Fallback |
|--------|--------|----------|
| Device | device_registry.json hostname match | os.uname() heuristic |
| Node | UMHNodeRegistry.primary_node() | os.uname().nodename |
| State | WorkspaceObservationEngine.latest() | ContextEngine health |

### Checkpoint Classification (deterministic)

| Age | Status |
|-----|--------|
| < 5 min | CURRENT |
| < 1 hour | RESUMABLE |
| < 24 hours | STALE |
| > 24 hours | LOST |
| Past expires_at | LOST |

---

## Files

### New (8)
| File | Layer | Lines |
|------|-------|-------|
| substrate/operator/operator_presence.py | substrate | 210 |
| substrate/operator/continuity_engine.py | substrate | 310 |
| substrate/operator/presence_timeline.py | substrate | 170 |
| substrate/operator/device_continuity.py | substrate | 130 |
| transports/api/cockpit_operator_presence_routes.py | transport | 100 |
| cockpit/src/renderer/stores/presenceStore.ts | cockpit | 105 |
| cockpit/src/renderer/panels/OperatorContinuityPanel.tsx | cockpit | 195 |
| tests/test_phase32_presence_continuity.py | tests | 930 |

### Modified (3)
| File | Change |
|------|--------|
| substrate/canonical_types.py | +12 type registrations |
| substrate/operator/__init__.py | +Phase 32 docstring block |
| transports/api/cockpit.py | +_mount_operator_presence_router() |

---

## API Routes (6)

| Route | Method | Purpose |
|-------|--------|---------|
| /presence | GET | Full presence snapshot |
| /presence/current | GET | Current context |
| /presence/checkpoints | GET | Resume checkpoints |
| /presence/timeline | GET | Presence transitions |
| /presence/devices | GET | Device continuity |
| /presence/resume | GET | Suggested resume state |

---

## Test Coverage (108 tests)

| Class | Tests |
|-------|-------|
| TestPresenceStateEnum | 4 |
| TestPresenceDeviceTypeEnum | 3 |
| TestContinuityStatusEnum | 2 |
| TestOperatorPresence | 4 |
| TestActiveContext | 4 |
| TestContinuityCheckpoint | 5 |
| TestPresenceSnapshot | 5 |
| TestContinuityEngine | 16 |
| TestCheckpointClassification | 5 |
| TestPresenceTransition | 4 |
| TestPresenceTimeline | 12 |
| TestDevicePresenceState | 4 |
| TestDeviceContinuityTracker | 9 |
| TestTypeRegistration | 12 |
| TestCockpitRoutes | 6 |
| TestIntegration | 13 |

---

## Gate Results

| Gate | Status |
|------|--------|
| Type divergence | CLEAN |
| Dependency direction | CLEAN |
| Instance leak | CLEAN |
| Projection leak | CLEAN |
| Phase 31 regression | CLEAN (86/86 still passing) |

---

## Live Verification

```
State: active
Device: vps
Device ID: vps
Node ID: umh-vps
Checkpoints: 0 (no active workspace observation)
Resume: device=vps, state=active, pending_approvals=0
```

---

## Design Decisions

1. **OperatorContinuityPanel.tsx instead of PresencePanel.tsx** — Phase 8/14
   already has a PresencePanel with tabs, attention model, activation flow.
   Phase 32 creates a new panel for the different concern (device continuity,
   resume suggestions, checkpoints).

2. **cockpit_operator_presence_routes.py** — named to distinguish from
   existing cockpit_presence_routes.py (Phase 14 activation/command routes).

3. **PresenceDeviceType maps to device_registry.json** — uses device_type
   values (vps/pc/tablet/mobile) not display names. Avoids device naming
   protocol violation.

4. **No surveillance, no control** — observation only. ContinuityEngine reads
   existing subsystem state. Never writes, never controls, never automates.

---

## Topology Stack

```
Phase 27 → Workspace Topology (repos, runtimes, devices)
Phase 28 → Node Topology (roles, services, versions)
Phase 29 → State Topology (domains, authority, coherence)
Phase 30 → Service Topology (dependencies, failure impact)
Phase 31 → Operator Home (aggregation façade, attention, timeline)
Phase 32 → Presence & Continuity (operator state across devices)
```

Phase 32 is the bridge from "infrastructure that knows itself" to
"infrastructure that serves a person."

---

## What This Phase Does NOT Do

- No surveillance
- No autonomous execution
- No keyboard/mouse automation
- No remote desktop control
- No new authority systems
- No new routing systems
- No LLM calls — deterministic observation only
- No modification to Phase 14 presence routes (activation, commands)
- No modification to Phase 25-31 systems
