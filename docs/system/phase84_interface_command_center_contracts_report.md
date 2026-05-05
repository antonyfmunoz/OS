# Phase 84 — Interface Layer + Command Center Contracts v1

**Date**: 2026-05-03
**Status**: Complete
**Invariants**: INV-581 through INV-610 (30 invariants)
**Hard rules**: 17
**Tests**: 171 passing
**Regression**: 1057 passing (Phase 75B–83)

## Summary

Phase 84 defines the official interface contract layer for UMH. It establishes
typed surface contracts, command envelopes, event models, deterministic state
machines, six-line voice-wave state, approval/notification views, surface
registry, safety boundaries, and Command Center read models. This is contracts
ONLY — no frontend, no voice runtime, no native overlay, no adapter
implementation, no execution from interface modules.

## New Modules in `umh/interface/`

| Module | Purpose | Lines |
|--------|---------|-------|
| `surfaces.py` | Surface taxonomy — 17 types, 11 platforms, 8 statuses, 22 capabilities | 465 |
| `commands.py` | Typed command envelopes with routing and validation | 318 |
| `events.py` | Descriptive event model (always read-only) | 173 |
| `state_machine.py` | Deterministic UI mode transitions | 249 |
| `voice_wave.py` | Six-line voice-wave glyph state (no audio) | 217 |
| `approval_views.py` | Governance approval display contracts (no mutation) | 190 |
| `notification_views.py` | Display-only notification records (no sending) | 184 |
| `surface_registry.py` | Registered surfaces with query capabilities | 127 |
| `safety.py` | Static analysis guardrails for interface layer | 256 |
| `command_center.py` | Command Center read model snapshot assembly | 125 |

## Surface Taxonomy

17 surface types: Command Center, Desktop Overlay, Floating Operator,
Minimized Voice Wave, Ghost Mode, Voice Interface, Telegram, Discord,
Mobile App, Mobile Widget, Live Activity, Shortcut, Browser Extension,
CLI, API, Developer Console, Unknown.

11 platforms: Windows, macOS, Linux, iOS, Android, Web, Browser, Terminal,
Telegram, Discord, Unknown.

22 capabilities declared per surface. iOS surfaces explicitly document:
"No true global overlay on iOS" and "No Siri replacement."

## Command Envelope Pattern

15 command types classified as read-only vs execution-intent.
`_READ_ONLY_TYPES` frozenset enforces that read queries, dashboard queries,
notification acks, mode changes, and surface state changes never require
governance. `_ROUTE_MAP` maps each command type to its route target
(e.g., `READ_QUERY` → observability, `EXECUTION_INTENT` → control_plane).

## Event Model

22 typed event types covering surface lifecycle, commands, approvals,
notifications, voice states, execution status, and dashboard refresh.
All events have `read_only=True` enforced. Batch assembly with configurable
limit (default 100).

## State Machine

10 interface modes: full_screen, windowed, expanded_overlay, minimized_wave,
ghost, hidden, voice_only, mobile, terminal, unknown.

15 allowed transitions in `_ALLOWED_TRANSITIONS` frozenset. HIDDEN is always
reachable from any visible mode. Same-mode transitions return NOOP.
Unknown mode always returns UNSUPPORTED.

## Voice Wave State Model

9 states: IDLE, LISTENING, THINKING, SPEAKING, MUTED, ERROR,
ATTENTION_REQUIRED, EXECUTING, UNKNOWN.

6-line pattern per state using LOW/MEDIUM/HIGH/PULSE/OFF line states.
Accessible labels for screen reader support. All transitions allowed
except transitions to UNKNOWN. DEFAULT_LINE_COUNT = 6.

## Approval Views

6 surface actions: APPROVE, DENY, ESCALATE, REQUEST_MORE_INFO, DEFER, UNKNOWN.
ApprovalRequestView includes consequences, reversible, expires_at.
ApprovalResponseEnvelope is envelope-only — Phase 84 does not mutate
governance state. Validation warns: "Phase 84: envelope only, no mutation."

## Notification Views

13 notification types including HEARTBEAT and REMINDER (type only, no runtime).
5 priority levels. 9 channels (declared, not implemented). 6 statuses.
InterfaceNotification links to related_trace_id, related_approval_id,
related_memory_candidate_id. No external sending.

## Surface Registry

InterfaceSurfaceRegistry provides register, get, list, query_by_capability,
build_capability_matrix, explain_limitations, find_best_surface_for_capability.
No destructive methods (no delete, remove, clear, pop).
`build_default_surface_registry()` loads 15 default surfaces.

## Safety Boundaries

7 forbidden pattern categories scanned via regex and AST:
1. Adapter imports
2. Subprocess calls
3. Network calls (requests, httpx, urllib, aiohttp, socket)
4. Storage mutation (db, cursor, execute, commit, INSERT, UPDATE, DELETE)
5. Governance mutation (approve_action, deny_action, escalate_action)
6. Trace mutation (store_trace, persist_trace, save_trace)
7. Memory promotion (promote_memory, persist_memory, save_to_long_term)

`validate_interface_module_boundaries()` scans all .py files in umh/interface/
(skipping safety.py itself).

## Command Center

12 sections: DASHBOARD, ACTIVITY, APPROVALS, TRACES, MEMORY, REGISTRY,
ONTOLOGY, STORAGE, MIGRATION, WORKSTATION, SETTINGS, UNKNOWN.

`build_command_center_snapshot()` assembles optional subsystem data.
Missing components produce warnings, not crashes. All fields optional.

## Integration Points

### Registry (Phase 80)
- 7 new `RegistryType` values: INTERFACE_SURFACE, INTERFACE_COMMAND, INTERFACE_EVENT, COMMAND_CENTER_SECTION, VOICE_WAVE_STATE, NOTIFICATION_CHANNEL, APPROVAL_SURFACE
- 4 bridge functions in `umh/registry/bridges.py`
- Interface metadata loaded in default catalog

### Observability (Phase 79)
- `interface_status` field in `SystemStatus`
- `check_interface_status()` function
- `interface_summary` in `OperatorDashboardSnapshot`

### Control Plane API (10 endpoints)
- GET `/interface/status` — interface health
- GET `/interface/surfaces` — registered surfaces
- GET `/interface/surfaces/{surface_id}` — single surface
- GET `/interface/capability-matrix` — surface capabilities
- GET `/interface/command-center` — snapshot
- GET `/interface/voice-wave` — voice wave state
- GET `/interface/notifications` — notification list
- GET `/interface/approvals` — pending approvals
- GET `/interface/safety` — safety scan results
- POST `/interface/commands/validate` — command validation (no execution)

### Control Plane CLI (8 commands)
- `interface-status`, `interface-surfaces`, `interface-matrix`
- `interface-command-center`, `interface-voice-wave`
- `interface-notifications`, `interface-approvals`, `interface-safety`

All endpoints and commands are read-only. No mutation. No execution.

## Files Modified

| File | Change |
|------|--------|
| `umh/registry/contracts.py` | +7 RegistryType enum values |
| `umh/registry/bridges.py` | +4 bridge functions |
| `umh/registry/catalog.py` | +4 interface catalog blocks |
| `umh/observability/system_status.py` | +interface_status field, +check function |
| `umh/interface/views.py` | +interface_summary field |
| `umh/observability/operator_views.py` | +interface_registry param, interface summary |
| `umh/control/api.py` | +10 endpoints (9 GET + 1 POST validate) |
| `umh/control/cli.py` | +8 commands, parsers, dispatch |

## Test Coverage (171 tests)

| Section | Tests | Description |
|---------|-------|-------------|
| 1. Surface Contracts | 20 | Normalization, serialization, defaults, iOS limits, capabilities |
| 2. Command Envelope | 14 | Normalization, serialization, validation, routing, read-only |
| 3. Events | 7 | Normalization, serialization, batch limit, read-only |
| 4. State Machine | 14 | Normalization, serialization, 7 transition scenarios |
| 5. Voice Wave | 13 | Normalization, 6-line default, 8 states, transitions, a11y |
| 6. Approval Views | 8 | Normalization, serialization, validation, no mutation |
| 7. Notification Views | 9 | 4 normalizations, serialization, ack, heartbeat, no send |
| 8. Surface Registry | 11 | Init, register, get, list, query, matrix, best surface, limits |
| 9. Interface Safety | 8 | Command safety, temp fixture detection, read-only |
| 10. Command Center | 12 | Normalization, degradation, optional components, warnings |
| 11. Registry Integration | 6 | Bridges, catalog, metadata-only, Phase 80 compat |
| 12. Observability | 6 | System status with/without interface, dashboard |
| 13. API | 4 | Endpoints registered, GET-only, POST validate, no execute |
| 14. CLI | 6 | Commands in parser, 5 smoke tests |
| 15. Layering | 15 | No subprocess/requests/browser/adapter/execution/mutation |
| 16. Regression | 9 | Phase 75B through 83 importable |

## Regression

All prior phase test suites pass (1057/1057 across Phase 75B–83).

## Doctrine Compliance

- No frontend code, no native UI (INV-581)
- No voice runtime, no audio processing (INV-582)
- No adapter implementation (INV-583)
- No execution from interface modules (INV-584)
- All events read-only (INV-585)
- State transitions deterministic (INV-586)
- Voice wave representational only (INV-587)
- Approval views display-only, no governance mutation (INV-588)
- Notifications display-only, no external sending (INV-589)
- Surface registry has no destructive methods (INV-590)
- Safety scanner is static analysis only (INV-591)
- Command Center is a read model (INV-592)
- All API endpoints read-only except POST validate (INV-593)
- All CLI commands read-only (INV-594)
- iOS limitations explicitly documented (INV-595)
- Unknown values degrade to UNKNOWN enum, never crash (INV-596)
- Missing components produce warnings, not errors (INV-597)
