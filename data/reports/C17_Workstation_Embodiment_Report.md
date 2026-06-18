# Campaign 17 — Workstation Embodiment & Operator Experience

## Summary
C17 creates the operator-facing MVP surface by composing 12+ existing C5-C16 subsystems into three presence runtimes + API routes + integration fills. No new intelligence domains. The operator experience loop is: interpret intent → resolve context → assess delegation → surface governance → track workstation state.

**Strongest invariant:** Right Rail = communication/clarification only. Top HUD = approval/governance actions. Meta IDE = governed build surface. Command Center = organism state. Execution only happens through governed work packets.

## Runtimes Built

### C17.0 — OrchestratorPresenceRuntime (orchestrator_presence_runtime.py)
- **Purpose**: Persistent orchestrator presence — mode, context, pending state
- **Mode classification**: LISTENING / CLARIFYING / PLANNING / WAITING_APPROVAL / MONITORING / DEGRADED
- **Composes**: OrchestratorAwarenessRuntime, OrganismStateRuntime, GovernedExecutionRuntime, ContextResolutionEngine, WorkspaceAwarenessRuntime, DeviceAwarenessRuntime, UnifiedApprovalRuntime, DelegationReadinessRuntime (8 deps)
- **API**: mode(), snapshot(), context(), interpret(text), active_device(), pending_approvals(), active_delegations(), summary()

### C17.1 — MetaIdeContextRuntime (meta_ide_context_runtime.py)
- **Purpose**: Read-only context binding for Meta IDE build surface
- **Does NOT replace**: existing Meta IDE loop routes (submit/advance/review/merge)
- **Composes**: ContextResolutionEngine, WorkspaceAwarenessRuntime, DeviceAwarenessRuntime, MetaIDEProjectionLoopRuntime, OrchestratorAwarenessRuntime (5 deps)
- **API**: context(), active_files(), resolve_intent(text), snapshot(), summary()

### C17.2 — WorkstationPresenceRuntime (workstation_presence_runtime.py)
- **Purpose**: Operator footprint — device, panel, project, recent actions
- **Ephemeral state**: active_panel, last_command (in-memory, not persisted)
- **Composes**: DeviceAwarenessRuntime, WorkspaceAwarenessRuntime, ContinuityEngine, UnifiedApprovalRuntime, DevicePresenceRegistry (5 deps)
- **API**: snapshot(), update_panel(), update_device(), update_context(), record_command(), last_command(), last_approval(), summary()

## Integration (C17.3)

### API Endpoints (3 route files)
- `GET /orchestrator-presence/snapshot` — orchestrator presence snapshot
- `GET /orchestrator-presence/context` — full orchestrator context
- `POST /orchestrator-presence/interpret` — resolve natural language to context
- `GET /meta-ide-context/context` — Meta IDE resolved context
- `GET /meta-ide-context/active-files` — active files list
- `POST /meta-ide-context/resolve-intent` — resolve work intent in IDE context
- `GET /workstation-presence/snapshot` — workstation presence snapshot
- `POST /workstation-presence/panel` — update active panel
- `POST /workstation-presence/device` — update active device
- `POST /workstation-presence/context` — update context

### Type Registrations (7)
- PresenceMode, OrchestratorPresenceSnapshot, OrchestratorPresenceRuntime
- MetaIdeContextSnapshot, MetaIdeContextRuntime
- WorkstationPresenceSnapshot, WorkstationPresenceRuntime

### Executive Brief + Strategic Context
- `_fill_workstation_presence()` adds: operator_device, presence_mode, active_panel
- `_fill_from_workstation_presence()` adds: workstation_presence dict

## Test Results
```
tests/test_orchestrator_presence_runtime.py     16 passed
tests/test_meta_ide_context_runtime.py          12 passed
tests/test_workstation_presence_runtime.py      14 passed
tests/test_workstation_mvp_loop.py               8 passed
─────────────────────────────────────────────────────────
TOTAL                                           50 passed (0.48s)
```

## Gate Checks
- Type divergence: clean (zero C17 violations)
- Dependency direction: clean (zero C17 violations)
- Instance context: clean (823 files scanned)
- Projection boundary: clean
- cockpit.py: 1,256 lines (under 3,000 limit)

## Key Design Decisions
1. **Composition over creation**: composes 12+ existing runtimes, zero new intelligence
2. **Deterministic-first**: zero LLM calls across all 3 runtimes
3. **Constructor injection**: `Any | None = None` for every dep, lazy loading with try/except
4. **interpret() for work-intent only**: casual messages bypass interpretation
5. **Meta IDE context is read-only**: does NOT replace existing Meta IDE loop routes
6. **No direct execution**: OrchestratorPresenceRuntime has no execute/approve/reject/dispatch methods (tested as invariant)
7. **Ephemeral workstation state**: panel/command tracking is in-memory, not persisted

## Files Created (12)
- `substrate/workstation/orchestrator_presence_runtime.py`
- `substrate/workstation/meta_ide_context_runtime.py`
- `substrate/workstation/workstation_presence_runtime.py`
- `transports/api/cockpit_orchestrator_presence_routes.py`
- `transports/api/cockpit_meta_ide_context_routes.py`
- `transports/api/cockpit_workstation_presence_routes.py`
- `data/reports/C17_Workstation_Embodiment_Report.md`
- `tests/test_orchestrator_presence_runtime.py`
- `tests/test_meta_ide_context_runtime.py`
- `tests/test_workstation_presence_runtime.py`
- `tests/test_workstation_mvp_loop.py`

## Files Modified (4)
- `substrate/canonical_types.py` — +7 type registrations
- `substrate/organism/executive_brief_runtime.py` — +`_fill_workstation_presence()`
- `substrate/organism/strategic_context_runtime.py` — +`_fill_from_workstation_presence()`
- `transports/api/cockpit.py` — +3 router mounts
