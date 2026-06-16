# Phase 31 — Cockpit Convergence & Operator Home

**Date:** 2026-06-15
**Status:** COMPLETE
**Tests:** 86/86 passing
**Lines:** ~1,700 new across 6 files, ~30 modified in 3 files

---

## What It Does

Phase 31 creates the first Jarvis Home Surface — a single OperatorContextEngine
that composes 6+ existing subsystems into one operator-facing view. No new
topology, no new registry, no new execution authority. Composition only.

The operator can now answer:
- Is the organism healthy?
- What needs attention?
- What changed recently?
- What is running?
- What is blocked?
- What requires approval?
- What work is active?
- What should I look at next?

Without opening any topology panel.

---

## Architecture

### OperatorContextEngine (aggregation façade)

Composes:
- **EventSpine** → timeline, critical event detection
- **ServiceFailureEngine** → service health, critical path, blast radius
- **StateCoherenceEngine** → state domain coherence, drift detection
- **UMHNodeRegistry** → node status, node count
- **ApprovalInterceptStore** → pending governance decisions
- **WorkspaceObservationEngine** → active workspaces, sessions

All dependencies lazy-loaded with try/except for graceful degradation.
Internal provider methods (`_get_*()`) maintain clean composition boundary.

### Attention Rules (deterministic)

| Condition | Severity | Type |
|-----------|----------|------|
| State domain drifted/stale | CRITICAL | STATE |
| Critical-priority event | CRITICAL | RUNTIME |
| Service blast_radius > 3 | WARNING | SERVICE |
| Pending approval > 0 | WARNING | GOVERNANCE |
| Node version drift | WARNING | RUNTIME |

---

## Files

### New (6)
| File | Layer | Lines |
|------|-------|-------|
| substrate/operator/operator_context.py | substrate | 210 |
| substrate/operator/operator_context_engine.py | substrate | 310 |
| transports/api/cockpit_operator_home_routes.py | transport | 105 |
| cockpit/src/renderer/stores/operatorHomeStore.ts | cockpit | 100 |
| cockpit/src/renderer/panels/OperatorHomePanel.tsx | cockpit | 230 |
| tests/test_phase31_operator_home.py | tests | 880 |

### Modified (3)
| File | Change |
|------|--------|
| substrate/canonical_types.py | +8 type registrations |
| substrate/operator/__init__.py | +Phase 31 docstring block |
| transports/api/cockpit.py | +_mount_operator_home_router() |

---

## API Routes (8)

| Route | Method | Purpose |
|-------|--------|---------|
| /operator/home | GET | Full snapshot |
| /operator/health | GET | Health summary |
| /operator/attention | GET | Attention queue |
| /operator/timeline | GET | Timeline feed |
| /operator/approvals | GET | Pending approvals |
| /operator/services | GET | Service alerts |
| /operator/nodes | GET | Node status |
| /operator/workspaces | GET | Active workspaces |

---

## Test Coverage (86 tests)

| Class | Tests |
|-------|-------|
| TestOperatorSeverityEnum | 4 |
| TestOperatorAttentionTypeEnum | 4 |
| TestOperatorAttentionItem | 6 |
| TestOperatorStatusCard | 4 |
| TestOperatorHealthSummary | 4 |
| TestOperatorTimelineEvent | 4 |
| TestOperatorSnapshot | 6 |
| TestOperatorContextEngine | 16 |
| TestAttentionGeneration | 10 |
| TestTimeline | 8 |
| TestCockpitRoutes | 6 |
| TestTypeRegistration | 4 |
| TestIntegration | 10 |

---

## Gate Results

| Gate | Status |
|------|--------|
| Instance leak | CLEAN |
| Projection leak | CLEAN |
| Dependency direction | CLEAN |
| Type divergence | CLEAN |
| Phase 30 regression | CLEAN (90/90 still passing) |

---

## Live Verification

```
Overall: degraded
  Services: 13 (degraded)    — event_spine blast_radius=5 triggers degraded
  State Domains: 10 (healthy) — all 10 domains coherent
  Nodes: 2 (healthy)          — VPS + Beast registered
  Workspaces: 0 (healthy)     — no active observation
Attention items: 4            — 4 services with blast_radius > 3
Timeline events: 0            — no EventSpine history in this session
Service alerts: 8             — all services with blast_radius > 0
```

---

## Design Decision: Aggregation Façade

OperatorContextEngine is NOT a new subsystem. It is a composition façade.
Cross-substrate import (operator/ → meta_ide/, organism/) is correct here
because the engine creates no new authority, state, or execution paths.

```
Topology phases:  Build sources of truth
Phase 31:         Consume sources of truth
```

---

## Topology Stack

```
Phase 27 → Workspace Topology (repos, runtimes, devices)
Phase 28 → Node Topology (roles, services, versions)
Phase 29 → State Topology (domains, authority, coherence)
Phase 30 → Service Topology (dependencies, failure impact, critical path)
Phase 31 → Operator Home (aggregation façade, attention, timeline)
```

Phase 31 is the convergence point where the operator stops navigating
subsystems and starts interacting with the organism as a whole.

---

## What This Phase Does NOT Do

- No new topology, graph, or registry
- No new execution authority
- No new routing system
- No new governance engine
- No LLM calls — deterministic aggregation only
- No modification to Phase 25-30 systems
- No removal of existing panels (they become drill-down surfaces)
- No new EventDomain — uses existing OPERATOR domain
