# Phase 5.5: Operational Metabolism Hardening

**Date**: 2026-05-27
**Scope**: Wire and harden existing Phase 5 modules into real running organism behavior
**Mandate**: No new abstractions. No UI redesign. No parallel systems. Wire what exists.

---

## 1. What Was Actually Running Before

The OrganismDaemon existed and was instantiated at os-operator startup, but its
metabolism was hollow:

- **daemon.tick()** called only `self._advisor.autonomous_tick()` — a single
  method on a single subsystem. The other 6 subsystems (HomeostasisEngine,
  RuntimeSupervisor, AllocationLoop, AsyncCoordinator, LeverageAssimilator,
  ProjectionPort) existed as classes but were never executed during ticks.

- **EventSpine** was in-memory only. On process restart, all organism events
  vanished. No crash recovery, no persistence.

- **ProjectionPort** had no subscriber persistence. Registered subscribers
  were lost on restart.

- **os-operator** created the daemon but never called `tick()` in a background
  loop. The daemon sat idle unless manually poked.

- **Cockpit WebSocket** had `push_organism_event()` wired but nothing called
  it — EventSpine emitted events to an empty subscriber list.

- **AutonomousTick engine** existed with adaptive cadence, failure isolation,
  and governed pause/kill but was never connected to the daemon.

**Net effect**: The organism was architecturally complete but metabolically dead.
Every subsystem existed. None continuously ran.

---

## 2. What Is Now Continuously Running

### daemon.py — Full Metabolism Wiring

Seven stages registered in AutonomousTick engine via `_register_tick_stages()`:

| Stage | Subsystem | What It Does |
|-------|-----------|-------------|
| advisor | Advisor | Drains signals, executes work units, health checks |
| homeostasis | HomeostasisEngine | System equilibrium monitoring |
| supervisor_reconcile | RuntimeSupervisor | Graph reconciliation |
| allocation | AllocationLoop | Continuous resource allocation cycles |
| async_objectives | AsyncCoordinator | Advances async objective queue |
| leverage_rebalance | LeverageAssimilator | Adaptive leverage scoring + degradation detection |
| projection_broadcast | _broadcast_state | Pushes state through ProjectionPort |

`daemon.tick()` now calls `self._autonomous_tick.execute_cycle()` which:
- Runs all registered stages with failure isolation per stage
- Adapts cadence based on work detected
- Returns structured report: `{cycle, stages_executed, stages_failed, elapsed_ms, had_work, stage_details}`
- Respects governor pause/kill signals

### operator_api.py — Background Tick Loop

New `_tick_loop(daemon)` async task created in FastAPI lifespan:
- Runs `daemon.tick()` at `daemon.autonomous_tick.current_interval` intervals
- Created as `asyncio.create_task()` on startup
- Cancelled cleanly on shutdown
- Daemon metabolism now runs continuously while os-operator is alive

### EventSpine → Cockpit WebSocket Bridge

New `_wire_spine_to_cockpit_ws(daemon)` subscribes EventSpine to call
`push_organism_event()` from the cockpit router. Every organism event now
flows to connected WebSocket clients in real time.

---

## 3. EventSpine Persistence Design

- **Format**: Append-only JSONL at `{store_dir}/events.jsonl`
- **Write**: Each `emit()` appends one JSON line (open/write/close per event)
- **Rotation**: When file exceeds 10MB (`_MAX_JSONL_BYTES`), renames to `.jsonl.old`
- **Recovery**: `recover()` reads JSONL, reconstructs `OrganismEvent` objects, appends to deque
- **Startup**: `daemon.start()` calls `self._event_spine.recover()` before first tick
- **Shutdown**: `daemon.stop()` calls `self._event_spine.flush()`

### ProjectionPort Persistence

- **Format**: JSON at `{state_dir}/projection_subscribers.json`
- **Write**: Atomic rewrite on `register()` / `unregister()`
- **Recovery**: `known_subscriber_ids()` reads persisted state for rehydration

---

## 4. Deployed Cockpit Verification

Endpoints verified on universalmetaharness.tech (routed through Fly.io → Tailscale socat → VPS :8091):

| Endpoint | Status | Notes |
|----------|--------|-------|
| `/api/umh/organism/snapshot` | 200 | Returns full organism state |
| `/api/umh/organism/runtimes` | 200 | Runtime graph data |
| `/api/umh/organism/governor` | 200 | Governor state |
| `/api/umh/organism/workcells` | 200 | Workcell registry |
| `/api/umh/execution/status` | 200 | Execution pipeline status |
| `/api/umh/pulse` | 200 | Health pulse |

New endpoints added in this phase:

| Endpoint | Transport | Purpose |
|----------|-----------|---------|
| `GET /organism/events?since=<ts>` | Polling | Incremental event fetch with `transport: "polling"` label |
| `GET /organism/tick` | Polling | Autonomous tick engine status |
| `WS /ws` | WebSocket | Real-time organism event push (existing, now wired) |

---

## 5. Validation Gates

| Gate | Result |
|------|--------|
| Organism tests | 54/54 PASSED |
| Full test suite | 336/336 PASSED |
| Instance leak | CLEAN (518 files) |
| Type divergence | Known pre-existing PrimitiveType (fixed in worktree as LeveragePrimitiveType, resolves on merge) |
| Dependency direction | CLEAN (substrate/ never imports transports/ or services/) |
| Compile check | All 7 modified files clean |

---

## 6. Files Modified

| File | Lines | Change |
|------|-------|--------|
| substrate/organism/daemon.py | 381 | +130: tick stages, metabolism wiring, governor/economy ownership |
| substrate/organism/event_spine.py | 290 | +90: JSONL persistence, rotation, recovery |
| substrate/organism/projection_port.py | 157 | +44: subscriber persistence, to_dict() |
| services/operator_api.py | 647 | +41: background tick loop, spine→WS bridge |
| transports/api/cockpit.py | 2256 | +25: /organism/events, /organism/tick endpoints |
| substrate/organism/tests/test_event_spine.py | 235 | +39: 4 new persistence tests |
| substrate/organism/tests/test_orchestration_integration.py | 480 | Updated assertions for new tick format |

---

## 7. Remaining Blockers

- **PrimitiveType divergence in main repo**: `substrate/organism/leverage_assimilation.py:59` defines `PrimitiveType` which shadows the canonical type. Worktree has the fix (`LeveragePrimitiveType`). Resolves when this branch merges.
- **No production deploy verification**: Changes are committed but os-operator container has not been restarted. Background tick loop will activate on next container restart.

---

## 8. Next Highest-Leverage Step

**Deploy and verify continuous metabolism in production.**

1. Restart os-operator container to activate background tick loop
2. Watch logs for `"organism daemon started"` with `tick_stages=7`
3. Verify WebSocket clients receive real-time organism events
4. Confirm JSONL file appears at the configured store_dir
5. Monitor tick cadence adaptation under real load

After production verification: the organism is metabolically alive and the cockpit
becomes a true real-time window into a living system rather than a snapshot viewer.
