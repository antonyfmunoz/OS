# Phase 27 — Workspace Runtime Graph

**Date:** 2026-06-15
**Status:** COMPLETE
**Tests:** 60/60 passing
**Lines:** ~1,706 new across 7 files, ~70 modified in 4 files

---

## What It Does

Phase 27 adds canonical workspace topology: engineering workspaces (UMH, CreatorOS, EntrepreneurOS, LyfeOS) are mapped to their repositories, runtimes, build targets, and devices. The organism can now reason about where work belongs and which device/runtime combination serves each workspace.

```
WorkspaceRegistry → WorkspaceTopologyEngine → WorkspaceRuntimeGraph
       ↑                     ↑ composes               ↓
  seed data         Phase 25 observations      live health enrichment
       +            Phase 24 device data
  device_registry.json
```

**Read-only topology only.** No execution, no deployment, no build authority.

---

## Architecture

### Data-Driven Workspaces

Workspaces are data (WorkspaceDefinition), not code. Each workspace defines its repositories, runtimes, build targets, and host devices. Adding a new workspace means registering a definition.

### Composition Pattern

WorkspaceTopologyEngine composes 3 existing subsystems:
- **WorkspaceRegistry** — canonical workspace definitions (seed + custom)
- **WorkspaceObservationEngine** (Phase 25) — live container/terminal/preview state
- **DistributedRuntime** (Phase 24) — device online status, worker counts

### Health Computation

| Condition | Health |
|---|---|
| All runtimes reachable + containers healthy | HEALTHY |
| Some containers unhealthy/down | DEGRADED |
| All containers down or all devices offline | BLOCKED |
| No observation data available | UNKNOWN |

---

## Seed Workspaces (4)

| workspace_id | Type | Device(s) | Runtimes | Build Targets |
|---|---|---|---|---|
| `umh` | core | vps | python, docker | linux, container |
| `creatoros` | product | beast | electron, react | windows |
| `entrepreneuros` | product | beast | electron, react | windows |
| `lyfeos` | product | beast | electron, react | windows |

---

## Files

### New (7)
| File | Layer | Lines |
|---|---|---|
| `substrate/meta_ide/workspace_runtime_graph.py` | substrate | 198 |
| `substrate/meta_ide/workspace_registry.py` | substrate | 243 |
| `substrate/meta_ide/workspace_topology_engine.py` | substrate | 206 |
| `transports/api/cockpit_workspace_topology_routes.py` | transport | 107 |
| `cockpit/src/renderer/panels/WorkspaceTopologyPanel.tsx` | cockpit | 158 |
| `cockpit/src/renderer/stores/workspaceTopologyStore.ts` | cockpit | 90 |
| `tests/test_phase27_workspace_runtime_graph.py` | tests | 704 |

### Modified (4)
| File | Change |
|---|---|
| `substrate/organism/runtime_graph.py` | +17 lines — 2 workspace query methods |
| `substrate/canonical_types.py` | +10 lines — 9 type registrations |
| `substrate/meta_ide/__init__.py` | +15 lines — Phase 27 exports |
| `transports/api/cockpit.py` | +15 lines — mount topology router |

---

## API Routes (6)

| Route | Method | Purpose |
|---|---|---|
| `/workspace-topology` | GET | Full workspace graph with health |
| `/workspace-topology/{id}` | GET | Single workspace with live summary |
| `/workspace-topology/{id}/health` | GET | Workspace health status |
| `/workspace-topology/{id}/runtimes` | GET | Workspace runtime list |
| `/workspace-topology/{id}/repositories` | GET | Workspace repository list |
| `/workspace-topology/{id}/build-targets` | GET | Workspace build target list |

---

## Test Coverage (60 tests)

| Class | Tests |
|---|---|
| TestWorkspaceTypes | 6 — enum values, string conversion |
| TestWorkspaceModels | 8 — construction, serialization, from_dict, roundtrip |
| TestWorkspaceRegistry | 10 — seed count, get by id, repo lookup, device lookup, register, no-seed |
| TestTopologyEngine | 10 — topology, health, summary, preferred build target, registry property |
| TestRuntimeGraphIntegration | 6 — workspace_for_runtime, runtimes_for_workspace |
| TestWorkspaceHealth | 6 — healthy/degraded/blocked/unknown derivation |
| TestCockpitRoutes | 4 — import, configure, router, singleton |
| TestTypeRegistration | 4 — canonical types, no collision, package import, lookup |
| TestIntegration | 6 — full chain, device consistency, topology completeness |

---

## Gate Results

| Gate | Status |
|---|---|
| Instance leak | CLEAN |
| Projection leak | CLEAN (pre-existing only) |
| Dependency direction | CLEAN (pre-existing only) |
| Type divergence | CLEAN (pre-existing only) |
| No file > 350 lines | CLEAN (largest: 243 lines) |

---

## Security Fix (Phase 26 post-merge)

Fixed `_get_operator_id()` fail-open to fail-closed in `cockpit_action_bridge_routes.py`:
- Returns 401 instead of falling back to shared `"operator"` identity
- `action_history` route now requires `Request` (no `None` default)
- Prevents cross-operator action visibility when auth state is missing

---

## What This Phase Does NOT Do

- No workspace creation/deletion at runtime (seed only)
- No build execution or deployment
- No routing changes — only graph enrichment queries
- No modification to existing WorkspacePanel.tsx
- No modification to existing cockpit_workspace_routes.py
- No changes to reality_mutation.py
- No LLM calls — deterministic lookup only
