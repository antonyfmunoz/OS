# W1 — Unified Compute & Execution Fabric — COMPLETE

## What Changed

ComputeFabricRuntime composes Phase 24 DistributedRuntime + Phase 28 UMHNodeTopology into a single unified view of all compute nodes.

The organism can now answer: **"Where should this work run?"** — deterministically, with human-readable rationale.

## Files Created
- `substrate/organism/compute_fabric_runtime.py` (454 lines) — ComputeFabricRuntime, ComputeNode, RoutingDecision, ComputeNodeType, ComputeNodeHealth
- `transports/api/cockpit_compute_fabric_routes.py` (88 lines) — 4 API endpoints
- `tests/test_compute_fabric_runtime.py` (519 lines) — 55 tests, all passing

## Files Modified
- `substrate/canonical_types.py` — 5 new type registrations
- `transports/api/cockpit.py` — _mount_compute_fabric_router() added

## Files Deleted (old plan direction cleanup)
- `substrate/operator/exit_registry.py`
- `substrate/operator/exit_analysis.py`

## Cockpit Routes (mounted, total route count: 814)
- GET /compute/fabric — all nodes with unified health
- GET /compute/health — aggregated fabric health summary
- GET /compute/executions — what's running where right now
- POST /compute/route — "where should this run?" with rationale

## Acceptance Test — Routing Decision Shape
```json
{
  "target_node_id": "dn-a1b2c3d4",
  "target_node_type": "vps",
  "reason": "Selected dn-a1b2c3d4 because it is healthy, has code_execution capability, has available worker capacity (4 slots), and is the best locality match for vps work.",
  "capability_match": ["code_execution"],
  "alternatives": ["dn-e5f6a7b8"],
  "confidence": 1.0
}
```

GPU routing correctly selects Windows Beast:
```json
{
  "target_node_id": "dn-e5f6a7b8",
  "target_node_type": "windows",
  "reason": "Selected dn-e5f6a7b8 because it is healthy, has gpu_available, code_execution capability capabilities, has available worker capacity (8 slots), and is the best locality match for home work.",
  "capability_match": ["gpu_available", "code_execution"],
  "alternatives": ["dn-a1b2c3d4"],
  "confidence": 1.0
}
```

## Verification Results
- 55/55 tests passing
- All 4 pre-commit gates clean (no new violations)
- All files under 3,000 lines
- No substrate/ imports from transports/ or services/
- Route mount verified: 4 compute routes in 814 total
- Import check passing
- py_compile passing on all new files

## What This Enables
All future subsystems (Meta IDE, Agent Fleet, Execution Surfaces) can consume the fabric for routing instead of separately querying distributed_runtime or node_topology.

Next: W3 Agent Fleet → W2 Meta IDE → W4 Embodiment → W5 Operator Migration
