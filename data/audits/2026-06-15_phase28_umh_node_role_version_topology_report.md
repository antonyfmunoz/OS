# Phase 28 — UMH Node Role & Version Topology

**Date:** 2026-06-15
**Status:** COMPLETE
**Tests:** 78/78 passing
**Lines:** ~1,100 new across 5 files, ~100 modified in 9 files

---

## What It Does

Phase 28 models UMH as one distributed organism running the same substrate across multiple nodes. VPS and Beast are not different UMHs — they are the same organism with different node roles, active services, capabilities, and workspace responsibilities.

```
UMH Organism (organism_id: "umh")
├── Node: umh-vps (device: vps)
│   ├── roles: orchestrator, control_plane, observer
│   ├── services: cockpit_api, governance, memory, event_spine,
│   │             distributed_runtime, action_bridge
│   └── workspaces: umh
│
└── Node: umh-windows (device: beast)
    ├── roles: workstation, builder, observer
    ├── services: meta_ide, workspace_observation, workstation_control,
    │             local_builder, vision_runtime, voice_runtime
    └── workspaces: umh, creatoros, entrepreneuros, lyfeos
```

**Version coherence is first-class.** Capability drift is expected. Version drift is detected and surfaced.

---

## Architecture

### Data-Driven Node Topology

Nodes are data (infra/umh_node_registry.json), not code. No projection names in substrate. Adding a future node (laptop, cloud builder) means adding a JSON entry.

### Composition Pattern

- **UMHNodeRegistry** loads from JSON config, provides lookup API
- **UMHVersionCoherenceEngine** composes registry to detect version drift
- **WorkspaceTopologyEngine** enriched with workspace_nodes() for node-workspace links
- **PacketRouter** enriched with node hints (does NOT override capability-first routing)
- **DistributedRuntime** gains node_topology() method

### Version Coherence Logic

| Condition | Status |
|---|---|
| All online nodes match git_commit + schema + migration | COHERENT |
| One or more online nodes differ | DRIFTED |
| No version info or all nodes offline | UNKNOWN |

---

## Seed Nodes (2)

| node_id | Device | Roles | Services | Workspaces |
|---|---|---|---|---|
| umh-vps | vps | orchestrator, control_plane, observer | cockpit_api, governance, memory, event_spine, distributed_runtime, action_bridge | umh |
| umh-windows | beast | workstation, builder, observer | meta_ide, workspace_observation, workstation_control, local_builder, vision_runtime, voice_runtime | umh, creatoros, entrepreneuros, lyfeos |

---

## Files

### New (5 code + 1 config + 1 test)
| File | Layer | Lines |
|---|---|---|
| substrate/organism/umh_node_topology.py | substrate | 228 |
| substrate/organism/umh_node_registry.py | substrate | 148 |
| substrate/organism/umh_version_coherence.py | substrate | 132 |
| infra/umh_node_registry.json | config | 49 |
| transports/api/cockpit_umh_node_routes.py | transport | 100 |
| cockpit/src/renderer/stores/umhNodeStore.ts | cockpit | 79 |
| cockpit/src/renderer/panels/UMHNodePanel.tsx | cockpit | 133 |
| tests/test_phase28_umh_node_role_version_topology.py | tests | 760 |

### Modified (9)
| File | Change |
|---|---|
| substrate/meta_ide/workspace_runtime_graph.py | +2 fields on WorkspaceDefinition, update to_dict/from_dict |
| substrate/meta_ide/workspace_registry.py | Parse new fields in _load_seed_workspaces() |
| substrate/meta_ide/workspace_topology_engine.py | +workspace_nodes() method |
| infra/workspace_registry.json | Add primary_umh_node_id + supporting_umh_node_ids, update UMH device_ids |
| substrate/organism/packet_router.py | +3 optional fields on PacketPlacement, node hints in route() |
| substrate/organism/distributed_runtime.py | +node_topology() method |
| substrate/canonical_types.py | +10 type registrations |
| substrate/organism/__init__.py | Update docstring |
| transports/api/cockpit.py | +mount_umh_node_router() |

---

## API Routes (7)

| Route | Method | Purpose |
|---|---|---|
| /umh-nodes | GET | Full node topology |
| /umh-nodes/{node_id} | GET | Single node detail |
| /umh-nodes/{node_id}/services | GET | Active services for node |
| /umh-nodes/by-role/{role} | GET | Nodes with a given role |
| /umh-nodes/by-service/{service_role} | GET | Nodes providing a service |
| /umh-nodes/version/status | GET | Overall version coherence |
| /umh-nodes/version/drift | GET | Per-node drift report |

---

## Test Coverage (78 tests)

| Class | Tests |
|---|---|
| TestUMHNodeTypes | 8 — enum values, counts |
| TestUMHVersionInfo | 6 — construction, serialization, matches |
| TestUMHServiceActivation | 4 — construction, serialization |
| TestUMHNodeModels | 8 — record + topology, roundtrip |
| TestUMHNodeRegistry | 10 — seed, get, by device/role/service/workspace, primary |
| TestSeedNodes | 6 — VPS orchestrator, Beast workstation, both UMH workspace |
| TestVersionCoherence | 8 — coherent/drifted/unknown, drift report |
| TestWorkspaceNodeLinks | 6 — UMH both nodes, CreatorOS primary Windows |
| TestRoutingHints | 6 — placement fields, capability-first preserved |
| TestCockpitRoutes | 4 — import, configure, router |
| TestTypeRegistration | 4 — canonical types, lookup |
| TestIntegration | 8 — full chain, composition, service resolution |

---

## Gate Results

| Gate | Status |
|---|---|
| Instance leak | CLEAN |
| Projection leak | CLEAN (pre-existing only) |
| Dependency direction | CLEAN (pre-existing only) |
| Type divergence | CLEAN (pre-existing only) |
| No file > 300 lines | CLEAN (largest: 228 lines) |
| Phase 27 regression | CLEAN (60/60 still passing) |

---

## Workspace Enrichment (Phase 27 update)

| Workspace | primary_umh_node_id | supporting_umh_node_ids | device_ids |
|---|---|---|---|
| umh | umh-vps | [umh-windows] | [vps, beast] |
| creatoros | umh-windows | [umh-vps] | [beast] |
| entrepreneuros | umh-windows | [umh-vps] | [beast] |
| lyfeos | umh-windows | [umh-vps] | [beast] |

---

## What This Phase Does NOT Do

- No execution authority
- No deployment or remote control
- No new device registry entries (composes existing infra/device_registry.json)
- No duplicate workspace or device registry
- No LLM calls — deterministic topology only
- No modification to existing DeviceNodeProfile or device_role_registry.py
- No modification to existing DistributedRuntime.device_summary() or topology() signatures
