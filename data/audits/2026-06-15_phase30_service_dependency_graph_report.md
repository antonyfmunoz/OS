# Phase 30 — Service Dependency & Failure Graph

**Date:** 2026-06-15
**Status:** COMPLETE
**Tests:** 90/90 passing
**Lines:** ~2,057 new across 8 files, ~30 modified in 3 files

---

## What It Does

Phase 30 models service-to-service architectural dependencies and computes failure impact across the UMH organism. Dependencies are Service→Service (architecture), not File→File (implementation).

```
UMH Service Dependency Critical Path
├── event_spine          blast_radius=5 (CRITICAL)
├── governance           blast_radius=4 (CRITICAL)
├── memory               blast_radius=4 (CRITICAL)
├── workspace_observation blast_radius=4 (SUPPORTING)
├── cockpit_api          blast_radius=1 (CRITICAL)
├── distributed_runtime  blast_radius=1 (CORE)
├── workstation_control  blast_radius=1 (SUPPORTING)
├── meta_ide             blast_radius=1 (SUPPORTING)
├── action_bridge        blast_radius=0 (SUPPORTING)
├── cockpit_frontend     blast_radius=0 (SUPPORTING)
├── vision_runtime       blast_radius=0 (OPTIONAL)
├── voice_runtime        blast_radius=0 (OPTIONAL)
└── local_builder        blast_radius=0 (OPTIONAL)
```

---

## Architecture

### Service Dependency Graph (observation only)
- **DependencyStrength** enum: REQUIRED, DEGRADED, OPTIONAL
- **ServiceCriticality** enum: CRITICAL, CORE, SUPPORTING, OPTIONAL
- **ServiceHealthImpact** enum: BLOCKED, DEGRADED, UNAFFECTED, UNKNOWN

### Composition Pattern
- **ServiceDependencyRegistry** loads from `infra/service_dependency_registry.json`
- **ServiceFailureEngine** composes ServiceDependencyRegistry + StateRegistry
- No modifications to Phase 28 (UMHNodeRecord) or Phase 29 (StateAuthority)

### Failure Impact Algorithm
1. Find direct dependents (services that depend ON the failed service)
2. BFS transitive dependents
3. Collect affected state domains from all impacted services
4. blast_radius = total unique affected services
5. severity = critical (>50%), high (>30%), medium (>0), low (0)

---

## Seed Data (13 services, 15 dependencies)

### Services

| Service | Criticality | Owner | State Domains |
|---------|------------|-------|---------------|
| cockpit_api | critical | umh-vps | configuration |
| cockpit_frontend | supporting | umh-vps | — |
| governance | critical | umh-vps | governance, proof, reality |
| memory | critical | umh-vps | memory |
| event_spine | critical | umh-vps | — |
| distributed_runtime | core | umh-vps | runtime, execution |
| action_bridge | supporting | umh-vps | — |
| meta_ide | supporting | umh-windows | — |
| workspace_observation | supporting | umh-windows | workspace, observation |
| workstation_control | supporting | umh-windows | session |
| vision_runtime | optional | umh-windows | — |
| voice_runtime | optional | umh-windows | — |
| local_builder | optional | umh-windows | — |

### Key Dependencies

| Source → Target | Strength |
|-----------------|----------|
| cockpit_frontend → cockpit_api | required |
| cockpit_api → governance | degraded |
| distributed_runtime → governance | required |
| action_bridge → governance | required |
| distributed_runtime → event_spine | degraded |
| meta_ide → workspace_observation | degraded |

---

## Files

### New (8)
| File | Layer | Lines |
|------|-------|-------|
| substrate/organism/service_dependency_graph.py | substrate | 166 |
| substrate/organism/service_dependency_registry.py | substrate | 139 |
| substrate/organism/service_failure_engine.py | substrate | 168 |
| infra/service_dependency_registry.json | config | 187 |
| transports/api/cockpit_service_graph_routes.py | transport | 108 |
| cockpit/src/renderer/stores/serviceGraphStore.ts | cockpit | 81 |
| cockpit/src/renderer/panels/ServiceGraphPanel.tsx | cockpit | 228 |
| tests/test_phase30_service_dependency_graph.py | tests | 980 |

### Modified (3)
| File | Change |
|------|--------|
| substrate/canonical_types.py | +9 type registrations |
| substrate/organism/__init__.py | +Phase 30 docstring block |
| transports/api/cockpit.py | +_mount_service_graph_router() |

---

## API Routes (7)

| Route | Method | Purpose |
|-------|--------|---------|
| /service-graph | GET | Full topology |
| /service-graph/services | GET | Service list |
| /service-graph/dependencies | GET | Dependency edges |
| /service-graph/impact/{service_role} | GET | Failure impact |
| /service-graph/critical-path | GET | Ranked critical path |
| /service-graph/leaf-services | GET | Leaf services |
| /service-graph/health | GET | Organism health |

---

## Test Coverage (90 tests)

| Class | Tests |
|-------|-------|
| TestDependencyStrengthEnum | 4 |
| TestServiceCriticalityEnum | 4 |
| TestServiceHealthImpactEnum | 4 |
| TestServiceDependency | 6 |
| TestServiceNode | 6 |
| TestFailureImpact | 6 |
| TestServiceDependencyTopology | 5 |
| TestServiceDependencyRegistry | 12 |
| TestServiceFailureEngine | 12 |
| TestSeedDataConsistency | 8 |
| TestCockpitRoutes | 4 |
| TestTypeRegistration | 4 |
| TestTopologyStackIntegration | 10 |
| TestCrossLayerQueries | 5 |

---

## Gate Results

| Gate | Status |
|------|--------|
| Instance leak | CLEAN |
| Projection leak | CLEAN |
| Dependency direction | CLEAN |
| Type divergence | CLEAN |
| No file > 300 lines | CLEAN (largest: 228 lines panel) |
| Phase 29 regression | CLEAN (84/84 still passing) |

---

## Topology Stack

```
Phase 27 → Workspace Topology (repos, runtimes, devices)
Phase 28 → Node Topology (roles, services, versions)
Phase 29 → State Topology (domains, authority, coherence)
Phase 30 → Service Topology (dependencies, failure impact, critical path)
```

The organism can answer:
- What services exist? → 13 services across 2 nodes
- What depends on Governance? → cockpit_api, distributed_runtime, action_bridge
- If EventSpine fails, what degrades? → 5 services (blast_radius=5)
- What services are critical path? → event_spine, governance, memory, workspace_observation
- What services are leaf nodes? → vision_runtime, voice_runtime, local_builder, action_bridge, cockpit_frontend
- What state domains are affected by governance failure? → governance, proof, reality + cascading
- Which service is highest risk? → event_spine (blast_radius=5)

---

## Cross-Layer Verification

All 10 state domains resolve to known services:
```
memory          → memory                    [OK]
governance      → governance                [OK]
runtime         → distributed_runtime       [OK]
workspace       → workspace_observation     [OK]
session         → workstation_control       [OK]
observation     → workspace_observation     [OK]
execution       → distributed_runtime       [OK]
proof           → governance                [OK]
reality         → governance                [OK]
configuration   → cockpit_api               [OK]
```

---

## What This Phase Does NOT Do

- No replication engine
- No synchronization daemon
- No automatic failover
- No execution authority
- No restart authority
- No modification to UMHNodeRecord (Phase 28) or StateAuthority (Phase 29)
- No LLM calls — deterministic topology only
