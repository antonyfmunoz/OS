# Phase 29 — Organism State Authority & Coherence

**Date:** 2026-06-15
**Status:** COMPLETE
**Tests:** 84/84 passing
**Lines:** ~1,200 new across 5 code files, ~60 modified in 7 files

---

## What It Does

Phase 29 declares which node is authoritative for each state domain in the UMH organism. State is modeled by DOMAIN (memory, governance, runtime), not by file or service. No replication. No synchronization. No consensus. Observation and authority modeling only.

```
UMH Organism State Authority
├── umh-vps (7 domains)
│   ├── MEMORY       (neon_postgres, service: memory)
│   ├── GOVERNANCE   (neon_postgres, service: governance)
│   ├── RUNTIME      (in_memory, service: distributed_runtime)
│   ├── EXECUTION    (neon_postgres, service: distributed_runtime)
│   ├── PROOF        (json_file, service: governance)
│   ├── REALITY      (json_file, service: governance)
│   └── CONFIGURATION (json_file, service: cockpit_api)
│
└── umh-windows (3 domains)
    ├── WORKSPACE    (json_file, service: workspace_observation)
    ├── SESSION      (in_memory, service: workstation_control)
    └── OBSERVATION  (in_memory, service: workspace_observation)
```

---

## Architecture

### State Authority Graph (observation only)
- **StateDomain** enum: 10 canonical domains
- **StateAuthorityLevel** enum: 5 authority levels (primary, secondary, cache, mirror, derived)
- **StateCoherenceStatus** enum: 4 coherence states (coherent, stale, drifted, unknown)

### Composition Pattern
- **StateRegistry** loads from `infra/state_authority_registry.json`, provides domain→node lookup
- **StateCoherenceEngine** composes StateRegistry + UMHNodeRegistry to detect authority coherence
- **WorkspaceTopologyEngine** enriched with `workspace_state_domains()` — derived from workspace→node→owned_domains chain
- **UMHNodeRecord** gains `owned_state_domains` field — loaded from seed data

### Coherence Logic

| Condition | Status |
|---|---|
| Authority node online, version matches | COHERENT |
| Authority node offline | STALE |
| Authority node last_seen > 1 hour | STALE |
| Authority node version drifted | DRIFTED |
| No authority info or node not found | UNKNOWN |

---

## Seed Authority Map (10 domains)

| Domain | Primary Node | Storage | Service Owner |
|---|---|---|---|
| memory | umh-vps | neon_postgres | memory |
| governance | umh-vps | neon_postgres | governance |
| runtime | umh-vps | in_memory | distributed_runtime |
| workspace | umh-windows | json_file | workspace_observation |
| session | umh-windows | in_memory | workstation_control |
| observation | umh-windows | in_memory | workspace_observation |
| execution | umh-vps | neon_postgres | distributed_runtime |
| proof | umh-vps | json_file | governance |
| reality | umh-vps | json_file | governance |
| configuration | umh-vps | json_file | cockpit_api |

---

## Files

### New (5 code + 1 config + 1 cockpit store + 1 cockpit panel + 1 test)
| File | Layer | Lines |
|---|---|---|
| substrate/organism/state_authority_graph.py | substrate | 131 |
| substrate/organism/state_registry.py | substrate | 108 |
| substrate/organism/state_coherence_engine.py | substrate | 174 |
| infra/state_authority_registry.json | config | 62 |
| transports/api/cockpit_state_authority_routes.py | transport | 99 |
| cockpit/src/renderer/stores/stateAuthorityStore.ts | cockpit | 66 |
| cockpit/src/renderer/panels/StateAuthorityPanel.tsx | cockpit | 106 |
| tests/test_phase29_state_authority_graph.py | tests | 801 |

### Modified (7)
| File | Change |
|---|---|
| substrate/organism/umh_node_topology.py | +owned_state_domains field on UMHNodeRecord |
| substrate/organism/umh_node_registry.py | Parse owned_state_domains in _load_seed_nodes() |
| substrate/meta_ide/workspace_topology_engine.py | +workspace_state_domains() method |
| infra/umh_node_registry.json | Add owned_state_domains arrays to both nodes |
| substrate/canonical_types.py | +8 type registrations |
| substrate/organism/__init__.py | Update docstring with Phase 29 |
| transports/api/cockpit.py | +mount_state_authority_router() |

---

## API Routes (5)

| Route | Method | Purpose |
|---|---|---|
| /state-authority | GET | Full state authority graph |
| /state-authority/domains | GET | All domain authorities |
| /state-authority/coherence | GET | Coherence report |
| /state-authority/domain/{domain} | GET | Single domain details + status |
| /state-authority/node/{node_id} | GET | Domains owned by a node |

---

## Test Coverage (84 tests)

| Class | Tests |
|---|---|
| TestStateDomainEnum | 6 |
| TestStateAuthorityLevel | 4 |
| TestStateCoherenceStatus | 4 |
| TestStateAuthorityModel | 6 |
| TestStateDomainStatusModel | 6 |
| TestOrganismStateGraph | 4 |
| TestStateRegistry | 10 |
| TestSeedAuthorities | 8 |
| TestStateCoherenceEngine | 8 |
| TestWorkspaceIntegration | 6 |
| TestNodeIntegration | 6 |
| TestCockpitRoutes | 4 |
| TestTypeRegistration | 4 |
| TestIntegration | 8 |

---

## Gate Results

| Gate | Status |
|---|---|
| Instance leak | CLEAN |
| Projection leak | CLEAN |
| Dependency direction | CLEAN |
| Type divergence | CLEAN |
| No file > 300 lines | CLEAN (largest: 174 lines) |
| Phase 28 regression | CLEAN (78/78 still passing) |

---

## Topology Stack

```
Phase 27 → Workspace Topology (repos, runtimes, devices)
Phase 28 → Node Topology (roles, services, versions)
Phase 29 → State Topology (domains, authority, coherence)
```

The organism can now answer:
- Where does Memory live? → umh-vps
- Who owns Governance? → umh-vps
- What node is authoritative for Workspace state? → umh-windows
- What becomes degraded if Beast disappears? → Workspace, Session, Observation
- What survives if VPS disappears? → Workspace, Session, Observation (on Beast)
- Which domains are stale? → coherence_report()
- Which domains are coherent? → organism_health()

---

## What This Phase Does NOT Do

- No replication engine
- No synchronization daemon
- No database clustering
- No distributed consensus
- No automatic failover
- No execution authority
- No deployment authority
- No modification to existing DeviceNodeProfile or device_role_registry.py
- No LLM calls — deterministic topology only
