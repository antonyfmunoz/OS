# Phase 11C — Cell Runtime + Control Plane Bridge v1

**Date**: 2026-04-29
**Status**: Complete
**Test Results**: 38/38 pass (11C cells) + 36/36 pass (11B brains) + 14/14 pass (11C brain context) + 34/34 pass (task decomposition)

## What was built

The Cell Runtime layer — specialized cognitive units that express substrate
context and request work through a control plane bridge, but NEVER directly
execute tools, adapters, subprocesses, or external systems.

## Architecture

```
User Objective
  → Control Plane
    → CellRuntime.spawn_cell(type)
      → CellContext (expression, scope, authority)
        → CellRuntime.request_execution(objective, operation)
          → CellExecutionRequest (frozen, append-only)
            → CellControlBridge.submit_request()
              → PlanObjective → create_plan() → execution spine
                → CellResult (delegated | pending | rejected)
                  → Signal/checkpoint
                    → Learning/correction (future phase)
```

### Key architectural boundary

```
┌─────────────────────────────────────────────────────────┐
│  CELL LAYER (umh/cells/)                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ models   │  │ runtime  │  │ registry │  │ bridge │ │
│  │ (types)  │  │ (life-   │  │ (type    │  │ (→ctrl │ │
│  │          │  │  cycle)  │  │  defs)   │  │  plane)│ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│       │              │              │            │      │
│  No execution    No adapters    No shell    Only calls  │
│  No subprocess   No tools       No docker   planner    │
└─────────────────────────────────────────────────────────┘
         │                                     │
    ┌────┴──────────┐              ┌───────────┴──────┐
    │ umh/brains/   │              │ umh/planning/    │
    │ (expression,  │              │ (PlanObjective,  │
    │  signals)     │              │  create_plan)    │
    └───────────────┘              └──────────────────┘
                                           │
                                   ┌───────┴──────┐
                                   │ Execution    │
                                   │ Spine        │
                                   └──────────────┘
```

## Cell vs Brain/Profile/Expression

| Concept | Layer | Purpose |
|---|---|---|
| BrainProfile | Identity | Immutable identity, authority, scope |
| ExpressionState | Expression | Mutable epigenetic config (amplify/silence/patterns) |
| BrainContext | Injection | Read-only view for intent/planning/decomposition |
| BrainSignal | Coordination | Append-only inter-brain messages |
| **Cell** | **Runtime** | **Lifecycle unit that expresses context and requests work** |
| CellIdentity | Cell identity | Immutable cell instance identity + lineage |
| CellContext | Cell scope | Objective, primitives, constraints, authority |
| CellExecutionRequest | Cell→Bridge | Frozen request for work (never executes) |
| CellResult | Bridge→Cell | Outcome status from control plane |

## Cell lifecycle

```
CREATED → HYDRATED → ACTIVE → WAITING → ACTIVE → ...
                         ↓
                    CHECKPOINTED → HYDRATED (resume)
                         ↓
                    TERMINATED (terminal)
                    FAILED (terminal)
```

- **CREATED**: Spawned but no context yet
- **HYDRATED**: Context loaded, ready to activate
- **ACTIVE**: Running, can request execution
- **WAITING**: Execution request submitted, waiting for result
- **CHECKPOINTED**: State saved, can be resumed via re-hydration
- **TERMINATED**: Clean shutdown, no further transitions
- **FAILED**: Error state, no further transitions

Invalid transitions raise `InvalidTransitionError`.

## How cells request execution without executing

1. Cell must be in ACTIVE status
2. `request_execution()` creates a frozen `CellExecutionRequest`
3. Request is appended to the request log (append-only)
4. Cell transitions to WAITING
5. Signal emitted: `cell.execution_requested`
6. Bridge `submit_request()` converts to `PlanObjective`
7. Existing `create_plan()` handles planning/validation
8. `CellResult` returned with status: DELEGATED, PENDING, or REJECTED
9. Cell never touches execution engine, adapters, or shell

## Files created

| File | Purpose |
|---|---|
| `umh/cells/__init__.py` | Package exports |
| `umh/cells/models.py` | CellType, CellStatus, CellIdentity, CellContext, CellCheckpoint, CellExecutionRequest, CellResult, RequestStatus enums and dataclasses |
| `umh/cells/runtime.py` | Cell lifecycle: spawn, hydrate, activate, checkpoint, terminate, fail, request_execution |
| `umh/cells/registry.py` | Cell type definitions, default types, custom registration |
| `umh/cells/bridge.py` | CellControlBridge: CellExecutionRequest → PlanObjective → create_plan |
| `tests/unit/test_phase11c_cells.py` | 38 tests across all contracts |
| `docs/audits/phase11c_cell_runtime_report.md` | This report |

## Files NOT modified

No existing files were modified. Phase 11C is purely additive.

## Invariant verification

| Invariant | Status |
|---|---|
| No execution imports in umh/cells/ | PASS (boundary test) |
| No adapter imports in umh/cells/ | PASS (boundary test) |
| No subprocess/docker/shell imports in umh/cells/ | PASS (boundary test) |
| No shell=True in umh/cells/ | PASS (boundary test) |
| Brain modules still execution-free | PASS (boundary test) |
| Cells cannot execute directly | PASS (request_execution creates request, doesn't run) |
| All cell signals append-only | PASS (uses existing BrainSignal store) |
| Phase 11B tests still pass | PASS (36/36) |
| Brain context tests still pass | PASS (14/14) |
| Task decomposition tests still pass | PASS (34/34) |
| Invalid transitions rejected | PASS (TERMINATED/FAILED are terminal) |

## Test coverage (38 tests)

- Model serialization: 9 tests (identity, context, request, result, checkpoint)
- Lifecycle: 8 tests (spawn, hydrate, activate, checkpoint, terminate, fail, full lifecycle, lineage)
- Invalid transitions: 4 tests (CREATED→ACTIVE blocked, TERMINATED terminal, FAILED terminal, double terminate)
- Execution requests: 3 tests (does not execute, emits signal, requires ACTIVE)
- Bridge: 2 tests (returns result, does not execute)
- Registry: 4 tests (default types, idempotent, custom type, serialization)
- List/query: 3 tests (list all, by status, nonexistent)
- Boundary safety: 5 tests (no subprocess, no adapters, no execution, no shell=True, brain modules clean)
- Phase 11B regression: 2 tests (imports, registry operations)

## Known limitations

1. **No persistence** — Cell state is in-memory only. Cells do not survive process restart.
2. **No async** — All operations are synchronous. Async cell operations would be a future phase.
3. **Bridge is plan-only** — The bridge routes through `create_plan()` but does not call `execute_plan()`. Actual execution follows the normal plan lifecycle.
4. **No CLI** — Skipped CLI surface to avoid overbuilding. Cell operations are API-only for now.
5. **No cell-to-cell communication** — Cells communicate through the shared signal store, not directly.

## Next recommended phase

**Phase 11D: Cell Orchestration + Multi-Cell Coordination**
- Cell-to-cell signal routing
- Orchestrated cell workflows (spawn chain: interpret → decompose → plan → review → request)
- Cell result callback / WAITING → ACTIVE resume
- Cell persistence (checkpoint → file or DB)
- CLI surface for cell operations
