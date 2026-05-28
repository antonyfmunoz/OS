# Phase 5.8 — Operational Leverage Engine + Reality Pressure Integration

**Date:** 2026-05-27
**Status:** COMPLETE
**Tests:** 77 new tests + 30 existing regression tests = 107 total, all passing

---

## Strategic Shift

Previous phases built organism infrastructure (metabolism, embodiment,
topology awareness, reconciliation, projection). Phase 5.8 shifts from
"can the organism run?" to "does the organism create massive operational
leverage?" Architecture now evolves from observed workload pressure,
not speculative expansion.

---

## Tracks Delivered

### Track A — Real Workload Integration
**File:** `substrate/organism/workload_probes.py`

Live operational probes that collect real environment state each tick:
- Docker container lifecycle and health (ps -a)
- Disk pressure (shutil.disk_usage with severity levels)
- Memory pressure (/proc/meminfo with severity levels)
- Repository state (branch, stale branches, stale worktrees, uncommitted)
- Process monitoring (tmux sessions, Python/Node counts)

All probes timeout-safe (10s max), failure-isolated, and emit events
through the EventSpine with pressure-level priority.

### Track B — Leverage Measurement System
**File:** `substrate/organism/leverage_metrics.py`

Measures actual organism value across six dimensions:
1. **Time compression** — actual vs estimated manual seconds
2. **Cognitive compression** — decisions automated without approval
3. **Operational reliability** — success rate
4. **Execution autonomy** — % tasks needing zero human involvement
5. **Economic efficiency** — cost per hour of saved labor
6. **Failure recovery speed** — MTTR

Composite LeverageScore formula weights time compression (0.25) highest.
Tracks: tasks, autonomous resolutions, interventions, escalations,
approvals, failures, retries, operator seconds saved, cost.

**API:** `GET /organism/leverage`

### Track C — Bottleneck Detection Engine
**File:** `substrate/organism/bottleneck_engine.py`

Detects 12 bottleneck categories:
- slow_runtime, overloaded_workcell, stalled_objective
- queue_buildup, retry_storm, dead_chain
- expensive_route, unused_runtime, repetitive_intervention
- failing_reconciliation, high_latency, high_failure_rate

Features:
- Configurable thresholds (BottleneckThresholds dataclass)
- Recurrence tracking — recurring bottlenecks auto-escalate to CRITICAL
- Correction suggestions for each category
- Event emission through EventSpine

**API:** `GET /organism/bottlenecks`

### Track D — Execution Pressure Loop
**Integrated into:** `substrate/organism/daemon.py`

New tick stages registered in the AutonomousTick engine:
1. `leverage_measurement` — computes leverage dimensions
2. `bottleneck_detection` — feeds real metrics into detector
3. `objective_physics` — analyzes causal structure
4. `operator_compression` — checks intervention patterns
5. `workload_probes` — collects live infrastructure state

The `_bottleneck_detection_tick` method feeds real data from:
- LeverageMetrics.bottleneck_inputs() (failure/retry/intervention rates)
- RuntimeGraph node stats (latency, idle cycles)
- AutonomousTick metrics (stage failure rate)
- ObjectiveQueue depth

### Track E — Objective Physics
**File:** `substrate/organism/objective_physics.py`

Models causal execution dynamics:
- Dependency chains with blocking node identification
- Execution gravity (resource-weighted centrality)
- Leverage propagation (transitive downstream compound effect)
- Critical paths (longest blocking chains)
- Strategic answers: what_matters_most(), what_blocks_everything()

Cycle-safe: handles circular dependencies in critical path computation.

**API:** `GET /organism/physics`

### Track F — Operator Compression
**File:** `substrate/organism/operator_compression.py`

Tracks operator burden and identifies automation candidates:
- Records autonomous vs manual actions
- Computes compression ratio (autonomous / total)
- Detects repeated intervention patterns
- Promotes to automation candidate when threshold (default: 3) exceeded
- Generates specific automation suggestions per intervention type
- Tracks total operator seconds consumed

**API:** `GET /organism/compression`

### Track G — Execution Modes
**File:** `substrate/organism/execution_modes.py`

Four governed execution classes:
1. **OBSERVE** — read-only, no mutations
2. **RECOMMEND** — produce action plans only
3. **ASSISTED** — require operator approval
4. **AUTONOMOUS** — bounded policy-controlled execution

Features:
- Auto-promotion: reliability >= threshold triggers promotion
- Auto-demotion: reliability drops below 0.5 triggers demotion
- Transition logging with reason and justification
- Decision tracking (proposed, approved, executed, result)
- Full audit trail

**API:** `GET /organism/execution-mode`

### Track H — Cockpit Leverage Surfaces
**File:** `transports/api/cockpit.py`

Seven new API routes:
- `GET /organism/leverage` — time saved, autonomous completions, dimensions
- `GET /organism/metrics` — all engine metrics in one payload
- `GET /organism/bottlenecks` — active bottlenecks, severity, recurrence
- `GET /organism/physics` — critical paths, gravity, blockers
- `GET /organism/compression` — automation candidates, compression ratio
- `GET /organism/workload` — live infrastructure state
- `GET /organism/execution-mode` — current mode, transition history

All routes source from substrate state — zero synthetic data.

### Track I — Reality Pressure Validation
**Validated through:**
- WorkloadProbes runs real subprocess calls (docker ps, /proc/meminfo, git)
- Bottleneck detection uses real tick metrics
- Tests exercise full daemon tick cycles with zero stage failures

### Track J — Validation + Audit
**Tests:** 77 new (7 test files), 30 existing regression = 107 total
- `test_leverage_metrics.py` — 9 tests
- `test_bottleneck_engine.py` — 13 tests
- `test_objective_physics.py` — 12 tests
- `test_operator_compression.py` — 7 tests
- `test_execution_modes.py` — 13 tests
- `test_workload_probes.py` — 10 tests
- `test_phase58_integration.py` — 13 tests (full daemon wiring)

---

## Daemon Wiring Summary

The OrganismDaemon now initializes and wires:
- LeverageMetrics → event_spine
- BottleneckEngine → event_spine
- ObjectivePhysics → event_spine
- OperatorCompression → event_spine
- ExecutionModeManager → event_spine
- WorkloadProbes → event_spine

All exposed as properties and included in `status()` output.
State broadcast includes leverage data through ProjectionPort.

---

## Files Changed

### New Files (6 engines + 7 test files)
| File | Lines | Purpose |
|------|-------|---------|
| `substrate/organism/leverage_metrics.py` | 218 | Leverage measurement |
| `substrate/organism/bottleneck_engine.py` | 262 | Bottleneck detection |
| `substrate/organism/objective_physics.py` | 260 | Causal dynamics |
| `substrate/organism/operator_compression.py` | 194 | Operator burden |
| `substrate/organism/execution_modes.py` | 274 | Execution autonomy |
| `substrate/organism/workload_probes.py` | 254 | Infrastructure probes |
| `substrate/organism/tests/test_leverage_metrics.py` | 127 | Tests |
| `substrate/organism/tests/test_bottleneck_engine.py` | 121 | Tests |
| `substrate/organism/tests/test_objective_physics.py` | 120 | Tests |
| `substrate/organism/tests/test_operator_compression.py` | 90 | Tests |
| `substrate/organism/tests/test_execution_modes.py` | 113 | Tests |
| `substrate/organism/tests/test_workload_probes.py` | 83 | Tests |
| `substrate/organism/tests/test_phase58_integration.py` | 196 | Integration tests |

### Modified Files
| File | Change |
|------|--------|
| `substrate/organism/daemon.py` | +6 engine imports, init, tick stages, properties, status |
| `substrate/organism/__init__.py` | Updated docstring with Phase 5.8 engines |
| `transports/api/cockpit.py` | +7 API routes (leverage, metrics, bottlenecks, physics, compression, workload, execution-mode) |

---

## Quality Gates

| Gate | Status |
|------|--------|
| All new files compile (py_compile) | PASS |
| Type divergence check (check_type_divergence.py) | PASS — no new divergence |
| Instance leak check (check_instance_leak.py) | PASS — zero leaks |
| No file > 3000 lines | PASS — largest is 779 (advisor.py) |
| substrate/ never imports from transports/ or services/ | PASS |
| All tests pass (77 new + 30 regression) | PASS |
| Zero tick stage failures across 3 integration cycles | PASS |
| Daemon imports cleanly | PASS |
| API routes compile | PASS |

---

## Next Leverage Frontier

The organism now has the measurement and detection infrastructure.
Next evolution should come from observed pressure:
1. Real workload execution (repo ops, Docker lifecycle, ingestion)
   driven by the probes and routed through ObjectivePhysics
2. Automation promotion — when OperatorCompression identifies a
   candidate, the system should propose an ExecutionMode upgrade
3. Cockpit visualization of leverage metrics, bottleneck topology,
   and critical paths
4. Cross-engine feedback: bottleneck detection → execution mode
   demotion; leverage improvement → execution mode promotion
