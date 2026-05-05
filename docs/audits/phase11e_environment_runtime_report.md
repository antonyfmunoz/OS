# Phase 11E — Environment Runtime + Secure Execution Layer v1

**Date:** 2026-04-29
**Status:** COMPLETE
**Tests:** 36 passed (11E) + 45 passed (11D) + 54 passed (11C) + 39 passed (11B) = 174 total

---

## Architecture

```
Cell → CellExecutionRequest → Control Plane → PlanObjective
                                                    │
                                                    ▼
                                           Execution Spine
                                                    │
                                                    ▼
                                        ┌── EnvironmentRuntime ──┐
                                        │                        │
                                        │  SandboxManager        │
                                        │    └── validate_task   │
                                        │                        │
                                        │  Scheduler             │
                                        │    └── select_node     │
                                        │                        │
                                        │  ContainerManager      │
                                        │    ├── create_container │
                                        │    ├── run_task         │
                                        │    └── destroy          │
                                        │                        │
                                        └── ExecutionResult ─────┘
                                                    │
                                                    ▼
                                        Control Plane → Signal → Cell resumes

Node Selection:
  NodeRegistry  →  Scheduler.select_node()
  ├── AVAILABLE filter
  ├── Resource match (cpu, mem, gpu)
  ├── Preference honor (LOCAL/VPS/CLOUD)
  ├── Latency-sensitive → prefer LOCAL
  ├── Load threshold (0.8) → fallback to VPS
  └── Best-of: lowest load, highest priority
```

**Doctrine preserved:**
- Cells decide WHAT (unchanged)
- Control plane approves (unchanged)
- Execution layer decides WHERE + HOW (new)
- Only execution layer touches environments (enforced via boundary tests)

---

## Modules Created

| File | Purpose | Lines |
|------|---------|-------|
| `umh/environments/models.py` | NodeType, NodeStatus, ExecutionIsolation, TaskStatus, ContainerStatus, SandboxVerdict, Node, ResourceRequirements, EnvironmentPermissions, ExecutionContext, ExecutionTask, ExecutionResult, ExecutionContainer | ~220 |
| `umh/environments/nodes.py` | NodeRegistry — thread-safe dynamic node registration | ~50 |
| `umh/environments/scheduler.py` | Deterministic, pure node selection | ~55 |
| `umh/environments/containers.py` | ContainerManager — simulated lifecycle abstraction | ~85 |
| `umh/environments/sandbox.py` | SandboxManager — pre-execution safety validation | ~100 |
| `umh/environments/runtime.py` | EnvironmentRuntime — full execution lifecycle orchestration | ~110 |
| `umh/environments/__init__.py` | Public API (21 exports) | ~50 |

---

## Integration with 11D

The environment layer sits BELOW the execution spine, called AFTER control plane approval:

```
11C: Cell → request_execution() → CellExecutionRequest
11D: CellOrchestrator → routes signals → workflow advancement
11E: EnvironmentRuntime.execute(task) → Node → Container → Result
```

No cross-contamination: cells cannot import `umh.environments`, and environments cannot import `umh.cells`.

---

## Node / Scheduler Model

- **Nodes** represent physical/virtual machines with typed resources (cpu, memory, gpu)
- **Scheduler** is a pure function: `select_node(task, nodes) → Node | None`
- Selection is deterministic: same task + same nodes = same result
- Load threshold at 0.8 triggers fallback to lower-load nodes
- GPU requirement filtering prevents scheduling on incapable nodes

---

## Sandbox Model

- **Pre-execution gate**: every task must pass `validate_task()` before running
- **Dangerous operations list**: `drop_table`, `delete_all`, `rm_rf`, `format_disk`, `self_modify_core`
- **Custom validators**: extensible via `register_validator()` for domain-specific safety rules
- **Audit trail**: all decisions logged via `list_decisions()`
- **Manual override**: `reject_execution()` for human-in-the-loop safety

---

## Execution Flow

```
ExecutionTask
  → SandboxManager.validate_task()
    → REJECTED? return immediately
  → Scheduler.select_node(task, available_nodes)
    → None? return FAILED
  → EnvironmentRuntime._create_context(node, task)
  → ContainerManager.create_container(node_id, context)
  → ContainerManager.run_task(container, task)
  → ContainerManager.destroy_container(container_id)  [always, in finally]
  → return ExecutionResult
```

---

## Invariants Verified

1. **No execution inside umh/cells** — boundary test confirms zero `umh.environments` imports in cell modules
2. **No subprocess/docker/shell** — boundary test across all environment modules
3. **No adapter imports** — environments import only from `umh.environments` and `umh.core`
4. **Container cleanup guaranteed** — `destroy_container()` in `finally` block
5. **Sandbox before execution** — rejected tasks never reach node selection
6. **Deterministic scheduling** — same inputs produce same node (tested)
7. **Resource filtering** — tasks cannot schedule on incapable nodes (tested)
8. **Cell modules unchanged** — 11B/11C/11D tests pass without modification

---

## Test Coverage

| Category | Count | Status |
|----------|-------|--------|
| Nodes | 5 | PASS |
| Scheduler | 6 | PASS |
| Containers | 5 | PASS |
| Sandbox | 5 | PASS |
| Runtime | 6 | PASS |
| Integration | 2 | PASS |
| Boundary | 4 | PASS |
| Regression | 3 | PASS |
| **Total** | **36** | **ALL PASS** |

---

## Known Limitations

1. **Simulated execution only** — ContainerManager doesn't run real containers
2. **No real Docker** — container lifecycle is in-memory simulation
3. **No distributed networking** — nodes are in-memory, no heartbeat/health checks
4. **No GPU scheduling** — GPU field exists but no real GPU detection
5. **No persistent node telemetry** — node state lost on restart
6. **No true security sandbox** — SandboxManager is structural, not OS-level isolation
7. **No task timeout enforcement** — timeout_s field exists but not enforced at runtime

All intentional for v1. Each is a clean extension point.

---

## Validation Commands

```bash
# Phase 11E tests
python3 -m pytest tests/unit/test_phase11e_environment_runtime.py -q --tb=short
# → 36 passed

# Phase 11D regression
python3 -m pytest tests/unit/test_phase11d_cell_orchestration.py -q --tb=short
# → 45 passed

# Phase 11C regression
python3 -m pytest tests/unit/test_phase11c_cells.py tests/unit/test_phase11c_brain_context.py -q --tb=short
# → 54 passed

# Phase 11B regression
python3 -m pytest tests/unit/test_phase11b_brains.py -q --tb=short
# → 39 passed

# Import check
python3 -c "from umh.environments import EnvironmentRuntime, NodeRegistry, ContainerManager, SandboxManager; print('OK')"
# → OK
```

---

## Is Phase 11F Safe?

**Yes.** Phase 11E is purely additive:
- No existing modules modified
- No existing imports changed
- All boundary invariants verified
- All regression tests pass

Phase 11F candidates:
- **Real container execution** — swap simulated ContainerManager for Docker-backed
- **Node discovery** — auto-detect local machine resources
- **Distributed node protocol** — VPS ↔ cloud node coordination
- **Timeout enforcement** — kill containers that exceed timeout_s
