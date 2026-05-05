# Phase 11F — Real Execution + Distributed Node Runtime v1

**Date:** 2026-04-30
**Status:** COMPLETE
**Tests:** 40 passed (11F) + 175 passed (11B–11E regression)

---

## What Changed: 11E → 11F

Phase 11E established the simulated execution layer — correct contracts,
lifecycle, and safety gates, but no real OS interaction. Phase 11F replaces
the simulation with real execution while preserving all invariants.

| Component | 11E (simulated) | 11F (real) |
|-----------|----------------|------------|
| Container execution | Hardcoded SUCCEEDED | subprocess.Popen / docker run |
| Sandbox | Operation name blocklist | + temp directory isolation, timeout validation |
| Scheduler | Static load values | + telemetry-informed selection |
| Telemetry | Did not exist | psutil / /proc fallback |
| Timeout | Not enforced | Process kill + FAILED result |
| Cleanup | Container status flip | + process termination, temp dir removal |

## Real Node Telemetry

`telemetry.py` (existed from late 11E, now integrated):
- `NodeTelemetry` dataclass: cpu_percent, memory_percent, available_memory, load_avg
- `TelemetryCollector`: psutil preferred, /proc/stat + /proc/meminfo fallback
- Returns safe defaults (0.0) if neither source available
- No global state — collector is injected into runtime

## Scheduler Upgrade

`scheduler.py` now accepts `telemetry: dict[str, NodeTelemetry] | None`:
- `_effective_load()` uses max(cpu%, mem%) from telemetry when available
- `_filter_by_telemetry()` excludes nodes with >85% memory when task needs more RAM
- Falls back to static `current_load` when no telemetry provided
- Remains a pure function — deterministic given same inputs

## Container Execution Modes

`containers.py` — two modes via `ExecutionMode` enum:

**SUBPROCESS mode:**
- `subprocess.Popen` with list-based args (no shell=True)
- Captures stdout/stderr with size limits (4KB)
- Timeout via `proc.communicate(timeout=N)` then `proc.kill()` on expiry
- Process tracking in `_processes` dict for destroy_container cleanup

**DOCKER mode:**
- `docker run --rm --network none --memory Nm --cpus N`
- Mounts sandbox work_dir as /workspace
- Kill via `docker kill` on timeout/error
- Auto-detected at init via `docker info`

Both modes always return `ExecutionResult` — never raise.

## Sandbox Enforcement

`sandbox.py` additions:
- Creates temp directory per task (`tempfile.mkdtemp`)
- Validates timeout bounds (1s–300s)
- `cleanup_task()` removes temp dir + contents
- `cleanup_all()` for batch cleanup
- `get_work_dir()` for runtime to pass to container

## Execution Flow

```
ExecutionTask
  -> SandboxManager.validate_task()     # gate + create work_dir
    -> REJECTED? return immediately
  -> TelemetryCollector.collect_local() # real system metrics
  -> select_node(task, nodes, telemetry) # informed placement
    -> no node? FAILED
  -> create ExecutionContext
  -> ContainerManager.create_container()
  -> ContainerManager.run_task(container, task, work_dir)
    -> timeout? kill + FAILED
    -> error? catch + FAILED
  -> destroy_container()               # always, via finally
  -> sandbox.cleanup_task()            # always, via finally
  -> return ExecutionResult
```

## Invariants Preserved

1. Cells NEVER execute anything
2. Cells NEVER import environments
3. All execution flows through control plane
4. Execution layer (containers.py) is the ONLY place using subprocess
5. No adapter bypass
6. Sandbox gates BEFORE execution
7. Environment always explicit
8. Cleanup ALWAYS happens (try/finally at both runtime and container level)

## Safety Guarantees

- No orphan processes: `destroy_container()` kills any tracked Popen
- No leftover temp directories: `cleanup_task()` in finally block
- No shell=True anywhere in environment modules
- No direct system calls (popen, etc.) outside containers.py
- subprocess only in containers.py — verified by boundary tests
- Timeout kills are hard kills (SIGKILL via proc.kill())

## Known Limitations

- Docker optional (auto-detected, falls back to subprocess)
- No distributed node discovery (single-machine telemetry applied to all nodes)
- No GPU scheduling
- Network sandbox is flag-only (Docker uses --network none, subprocess has no network isolation)
- No remote node execution
- psutil not installed on this VPS — uses /proc fallback

## Files Modified

- `umh/environments/models.py` — added ExecutionMode enum
- `umh/environments/containers.py` — real Docker + subprocess execution
- `umh/environments/sandbox.py` — temp directory isolation, timeout validation
- `umh/environments/scheduler.py` — telemetry-informed node selection
- `umh/environments/runtime.py` — real execution flow with cleanup
- `umh/environments/__init__.py` — updated exports

## Files Created

- `tests/unit/test_phase11f_execution_runtime.py` — 40 tests
- `docs/audits/phase11f_execution_runtime_report.md` — this file

## Files Updated (regression)

- `tests/unit/test_phase11e_environment_runtime.py` — adapted 2 tests for 11F reality

## Test Summary

| Suite | Tests | Result |
|-------|-------|--------|
| 11F execution runtime | 40 | all passed |
| 11E environment runtime | 37 | all passed |
| 11D cell orchestration | 41 | all passed |
| 11C cells | 44 | all passed |
| 11C brain context | 14 | all passed |
| 11B brains | 39 | all passed |
| **Total** | **215** | **all passed** |

## Is Phase 12 Safe?

Yes. The execution layer is now real but fully contained:
- All subprocess/Docker usage is in containers.py only
- Sandbox creates and destroys temp dirs per task
- Timeout enforcement prevents hangs
- No invariants broken
- Backward compatibility maintained (no-command tasks still work as simulated)

Phase 12 can safely build on this foundation for:
- Remote node execution
- GPU scheduling
- Network policy enforcement
- Persistent execution logs
