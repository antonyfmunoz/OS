# W1 — Unified Compute & Execution Fabric

## Context

After 35 phases + 10 gates, UMH's biggest bottleneck is no longer capability compounding — it's **compute fragmentation**. The operator bounces between ChatGPT → Claude Session → Termius → VPS → Windows Machine → Claude Session → ChatGPT because the organism cannot see, coordinate, or route work across its own compute as a single unified body.

The substrate already has most of the building blocks scattered across Phase 24 (distributed runtime) and Phase 28 (node topology). W1 composes them into one `ComputeFabricRuntime` that answers the critical question: **"Where should this work run?"** — deterministically, with rationale.

## Existing Infrastructure (reuse, don't rebuild)

### Phase 24 — Distributed Runtime (substrate/organism/)
- `worker_registry.py` — WorkerInstance, WorkerStatus, WorkerRegistry (register, unregister, heartbeat, stale detection, thread-safe)
- `device_role_registry.py` — DeviceRole (6 roles), DeviceCapability (16 capabilities), DeviceNodeProfile, load_registry(), seed_known_nodes()
- `device_capacity.py` — DeviceCapacity, DeviceCapacityModel (capacity_for, all_capacities, best_device_for_work)
- `packet_router.py` — PacketRouter, PacketPlacement (capability→worker→device routing)
- `distributed_runtime.py` — DistributedRuntime facade (overview, workers, capacity, topology, register_worker, route_packet)
- `runtime_fleet.py` — RuntimeProvider (11 types), RuntimeFleetMember, RuntimeSelection, RuntimeReadiness

### Phase 28 — Node Topology (substrate/organism/)
- `umh_node_topology.py` — UMHNodeRole (7 roles), UMHNodeStatus (4 statuses), UMHServiceRole (13 services), UMHNodeRecord, UMHNodeTopology, UMHVersionInfo
- `umh_node_registry.py` — UMHNodeRegistry (seed + topology generation)

### Other Relevant
- `substrate/operator/operator_presence.py` — PresenceState, PresenceDeviceType
- `substrate/workstation/work_lane.py` — LaneType, WorkLane, route_to_lane()
- `substrate/execution/runtime/capability_router.py` — Capability enum (28 capabilities)

## Gap Analysis — What's Missing

The existing infrastructure has all the primitives but lacks:

1. **ComputeNodeType enum** — a unified node type covering WINDOWS, VPS, CONTAINER, AGENT_SESSION, MODEL_RUNTIME (user spec). Currently scattered across DeviceRole + RuntimeProvider + UMHNodeRole with no single "what kind of compute is this?" enum.

2. **Unified health view** — WorkerRegistry has per-worker heartbeats, UMHNodeTopology has per-node status, but nothing composes these into a single health snapshot with freshness tracking.

3. **Execution routing with rationale** — PacketRouter routes capability→worker→device but doesn't explain WHY it chose that route. The user's acceptance test requires: "Where should this work run?" → answer WITH deterministic rationale.

4. **Active execution tracking** — WorkerInstance tracks current_task_id but there's no aggregated "what's running where right now" view across all compute nodes.

5. **Unified cockpit view** — Existing routes serve distributed-runtime (10 endpoints) and umh-nodes (6 endpoints) separately. No single `/compute/*` surface that composes both into the unified fabric view the operator needs.

## Deliverables

### D1 — ComputeFabricRuntime (`substrate/organism/compute_fabric_runtime.py`)

New composition facade that wires existing subsystems together. NOT a replacement — an aggregation layer.

```python
class ComputeNodeType(str, Enum):
    """Unified compute node classification."""
    VPS = "vps"
    WINDOWS = "windows"
    CONTAINER = "container"
    AGENT_SESSION = "agent_session"
    MODEL_RUNTIME = "model_runtime"

class ComputeNodeHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"

@dataclass
class ComputeNode:
    """Unified view of a compute node — composes DeviceNodeProfile + UMHNodeRecord + health."""
    node_id: str
    node_type: ComputeNodeType
    health: ComputeNodeHealth
    capabilities: list[str]
    active_workers: int
    max_workers: int
    active_executions: list[str]  # task IDs
    last_heartbeat: float
    metadata: dict[str, Any]

@dataclass
class RoutingDecision:
    """Deterministic routing answer with rationale."""
    target_node_id: str
    target_node_type: str
    reason: str                    # human-readable rationale
    capability_match: list[str]    # which capabilities matched
    alternatives: list[str]        # other eligible node IDs
    confidence: float              # 0.0-1.0

class ComputeFabricRuntime:
    """Unified compute fabric — composes DistributedRuntime + UMHNodeTopology + RuntimeFleet."""
    
    def __init__(self, distributed_runtime: DistributedRuntime):
        ...
    
    def nodes(self) -> list[ComputeNode]:
        """All compute nodes with unified health."""
    
    def health(self) -> dict[str, Any]:
        """Aggregated fabric health: total nodes, healthy/degraded/unreachable counts."""
    
    def capacity(self) -> dict[str, Any]:
        """Per-node capacity with utilization percentages."""
    
    def active_executions(self) -> list[dict[str, Any]]:
        """What's running where right now."""
    
    def route(self, capability_needs: list[str], risk_level: str = "low") -> RoutingDecision:
        """'Where should this work run?' — deterministic with rationale."""
    
    def register_node(self, node_id: str, node_type: str, capabilities: list[str]) -> ComputeNode:
        """Remote node registration (called via HTTP from Beast daemon)."""
    
    def heartbeat(self, node_id: str) -> bool:
        """Heartbeat from remote node. Updates last_seen + health."""
```

Compose from:
- `DistributedRuntime.overview()` for workers/capacity
- `UMHNodeRegistry.topology()` for node records
- `DeviceCapacityModel.best_device_for_work()` for routing
- `WorkerRegistry` for heartbeat/stale detection
- `RuntimeFleet` for provider readiness

### D2 — Cockpit API Routes (`transports/api/cockpit_compute_fabric_routes.py`)

**Existing routes (already live, DO NOT duplicate):**
- `cockpit_distributed_runtime_routes.py` — 10 endpoints under `/organism/distributed-runtime/*` (overview, devices, workers, capacity, assignments, capabilities, register, heartbeat, unregister, route)
- `cockpit_umh_node_routes.py` — 6 endpoints under `/umh-nodes/*` (topology, version status, drift, by-role, by-service, node detail)

**New routes (the unified fabric view):**
Following the `cockpit_spine_router.py` configure() pattern. New file creates the ComputeFabricRuntime internally, composing DistributedRuntime + UMHNodeRegistry:

```
GET  /compute/fabric       → fabric.nodes()            — all compute nodes with unified health (aggregates distributed-runtime + umh-nodes)
GET  /compute/health       → fabric.health()            — aggregated fabric health summary
GET  /compute/executions   → fabric.active_executions() — what's running where right now
POST /compute/route        → fabric.route()             — "where should this run?" with rationale
```

Note: /compute/register and /compute/heartbeat are NOT needed — the existing `/organism/distributed-runtime/workers/register` and `/workers/heartbeat` already handle this. The compute fabric routes are a **read layer** that composes existing subsystems.

Auth: `Depends(require_operator_dep)` on all routes.

### D3 — Tests (`tests/test_compute_fabric_runtime.py`)

Target: 40+ tests covering:
- Node aggregation from mock DistributedRuntime + UMHNodeRegistry
- Health computation (healthy when heartbeat fresh, degraded when stale, unreachable when very stale)
- Routing decisions with capability matching and rationale strings
- Route rejection when no capable node available
- Registration of new nodes
- Heartbeat updating last_seen
- Active execution tracking
- Capacity utilization math

### D4 — Cleanup

Delete premature files from old plan direction:
- `substrate/operator/exit_registry.py` (untracked)
- `substrate/operator/exit_analysis.py` (untracked)
- `data/umh/operator/` directory (empty)

## Files to Create

```
substrate/organism/compute_fabric_runtime.py      — ComputeFabricRuntime, ComputeNode, RoutingDecision, ComputeNodeType, ComputeNodeHealth (~300-400 lines)
transports/api/cockpit_compute_fabric_routes.py   — 4 API endpoints following configure() pattern (~100 lines)
tests/test_compute_fabric_runtime.py              — 40+ tests (~400 lines)
```

## Files to Modify

```
substrate/canonical_types.py                  — register ComputeNodeType, ComputeNodeHealth, ComputeNode, RoutingDecision
transports/api/cockpit.py                     — add _mount_compute_fabric_router() following exact Phase 24-28 pattern (import, configure, include_router)
```

## Files to Delete

```
substrate/operator/exit_registry.py           — premature, belongs to old plan direction (untracked)
substrate/operator/exit_analysis.py           — premature, belongs to old plan direction (untracked)
data/umh/operator/                            — empty directory from old plan (untracked)
```

## Implementation Order

1. **Delete** old exit_registry.py + exit_analysis.py + data/umh/operator/
2. **Create** `compute_fabric_runtime.py`:
   - Define ComputeNodeType, ComputeNodeHealth enums
   - Define ComputeNode, RoutingDecision dataclasses
   - Implement ComputeFabricRuntime composing DistributedRuntime + UMHNodeRegistry
   - nodes() aggregates from distributed_runtime.overview() + node_topology()
   - health() computes healthy/degraded/unreachable counts using heartbeat freshness
   - active_executions() reads from worker registry current_task_id
   - route() wraps packet_router with rationale string generation
3. **Register** new types in `canonical_types.py`
4. **Create** `cockpit_compute_fabric_routes.py` following configure() pattern from cockpit_distributed_runtime_routes.py
5. **Mount** routes in `transports/api/cockpit.py` — add `_mount_compute_fabric_router()` after the Phase 28 UMH Node Topology block (~line 600), following the exact pattern: import → configure(require_operator_dep=_require_operator_role) → router.include_router()
6. **Create** `test_compute_fabric_runtime.py`
7. **Verify** — imports, pre-commit gates, test suite, py_compile, wc -l

## Acceptance Test

The user's exact acceptance test:

> **"Where should this work run?"** → UMH answers with deterministic rationale

```python
from substrate.organism.compute_fabric_runtime import ComputeFabricRuntime
# ... setup with DistributedRuntime ...
decision = fabric.route(capability_needs=["gpu_available", "code_execution"], risk_level="low")
assert decision.target_node_id  # non-empty
assert decision.reason           # human-readable rationale
assert decision.capability_match # which capabilities matched
assert decision.confidence > 0   # routing confidence
```

## Verification

1. `python3 -c "from substrate.organism.compute_fabric_runtime import ComputeFabricRuntime, ComputeNode, RoutingDecision; print('import ok')"`
2. `python3 -m pytest tests/test_compute_fabric_runtime.py -v` — 40+ tests pass
3. `python3 -m py_compile substrate/organism/compute_fabric_runtime.py`
4. `python3 -m py_compile transports/api/cockpit_compute_fabric_routes.py`
5. All 4 pre-commit gates pass: `python3 scripts/check_type_divergence.py --all && python3 scripts/check_dependency_direction.py --all && python3 scripts/check_projection_leak.py --all && python3 scripts/check_instance_leak.py --all`
6. No file over 3,000 lines (`wc -l` check)
7. No substrate/ imports from transports/ or services/
8. Route test: POST to /compute/route with capability_needs → get RoutingDecision with rationale

## What This Does NOT Do

- Does NOT replace DistributedRuntime, WorkerRegistry, or UMHNodeTopology — composes them
- Does NOT introduce LLM calls — fully deterministic (Deterministic-First Principle)
- Does NOT create new type systems — reuses existing DeviceCapability, RuntimeProvider, etc. and adds only the missing ComputeNodeType
- Does NOT touch cockpit frontend — API routes only (frontend is a separate phase)
- Does NOT deploy anything — substrate code only, no Docker/Fly changes
