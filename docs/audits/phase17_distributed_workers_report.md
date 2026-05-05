# Phase 17 Audit Report — Remote Execution Daemon + Distributed Worker Runtime v1

**Date:** 2026-04-29
**Status:** PASS — all invariants verified
**Tests:** 61/61 passed | Regression: 538/538 passed (phases 11B–17, zero regressions)

---

## Deliverables

| # | Deliverable | File | Status |
|---|-------------|------|--------|
| 1 | `JobLock` + `JobLockManager` | `umh/jobs/locking.py` | DONE |
| 2 | `claim_job()` on JobStore | `umh/jobs/store.py` | DONE |
| 3 | `WorkerLoop` + `ExecutionResult` + `WorkerStats` | `umh/nodes/worker.py` | DONE |
| 4 | `NodeDaemon` + `DaemonConfig` + `DaemonMode` | `umh/nodes/daemon.py` | DONE |
| 5 | `Distributor` | `umh/runtime/distributor.py` | DONE |
| 6 | `umh/jobs/__init__.py` exports | `umh/jobs/__init__.py` | DONE |
| 7 | `umh/nodes/__init__.py` exports | `umh/nodes/__init__.py` | DONE |
| 8 | `umh/runtime/__init__.py` exports | `umh/runtime/__init__.py` | DONE |
| 9 | Test suite | `tests/unit/test_phase17_distributed_workers.py` | DONE — 61 tests |

---

## Architecture

### Pull Model (vs Push)

Previous phases used a push model: the control plane assigns work to specific nodes. Phase 17 inverts this with a pull model:

```
Distributor               JobStore                 Workers
    |                        |                        |
    |-- submit_job() ------->|                        |
    |                        |<--- claim_job() -------|
    |                        |--- SUBMITTED->RUNNING->|
    |                        |<--- mark_succeeded() --|
```

Workers autonomously poll the store, claim SUBMITTED jobs, execute them, and update state. The control plane only submits — it never forces assignment.

### Job Locking

```
JobLockManager
  ├── acquire_lock(job_id, node_id) → JobLock | None  (atomic, TTL-based)
  ├── release_lock(job_id)          → bool
  ├── is_locked(job_id)             → bool            (auto-expires stale locks)
  └── clear_expired()               → int
```

Prevents double execution: two workers polling simultaneously cannot both claim the same job. The lock is acquired inside `claim_job()` under the store's threading lock.

### Atomic Claiming Flow

```python
def claim_job(node_id):
    with self._lock:                    # store-level threading lock
        find SUBMITTED job (oldest first)
        acquire_lock(job_id, node_id)   # lock manager check
        transition(job, RUNNING)        # lifecycle validation
        job.node_id = node_id           # ownership assignment
    persist(job)                        # durable write
    return job
```

All three operations (find, lock, transition) happen under a single lock — no race window.

### Worker Loop

```
WorkerLoop
  ├── poll_once() → claim, execute, update state
  ├── executor callback → caller decides HOW to execute
  └── stats tracking (claimed, succeeded, failed, polls)
```

The executor callback pattern keeps subprocess out of the worker module. The caller provides a function that receives an ExecutionJob and returns an ExecutionResult.

### Daemon Lifecycle

```
NodeDaemon
  ├── start() → activates worker + emits initial heartbeat
  ├── tick()  → poll_once + periodic heartbeat
  ├── stop()  → deactivates worker
  └── heartbeat includes: active_job_id, stats, mode
```

### Failure Recovery

| Scenario | Detection | Recovery |
|----------|-----------|----------|
| Worker dies mid-job | Heartbeat goes stale | Node marked OFFLINE → job ORPHANED → retry |
| Lock expires | TTL check on acquire | Lock auto-released → job claimable |
| Duplicate claim attempt | Lock manager | Second claim returns None |
| Executor crashes | Exception caught | Job marked FAILED, stats updated |
| No executor configured | Checked before execution | Job immediately FAILED |

---

## Hard Invariants

| # | Invariant | Verified |
|---|-----------|----------|
| 1–19 | All prior phase invariants | YES — 477 prior tests pass |
| 20 | No job executes twice concurrently | YES — lock + atomic claim |
| 21 | Job ownership explicit (node_id) | YES — claim_job sets node_id |
| 22 | Workers do NOT bypass control plane | YES — workers use store API only |
| 23 | Worker cannot mutate job state illegally | YES — all mutations via lifecycle.transition() |
| 24 | Job claiming is atomic | YES — under store._lock, lock+transition+assign |

---

## Test Coverage Summary

| Category | Count | Description |
|----------|-------|-------------|
| Locking | 12 | acquire, double-lock, expiry, release, clear |
| Claiming | 6 | basic claim, double prevention, FIFO, no-work |
| Worker | 10 | pick job, stats, failure, crash, stop, lock release |
| Daemon | 9 | start/stop, tick, heartbeat, config, modes |
| Distributor | 6 | submit, preferred node, pending, status |
| Failure handling | 3 | worker death→orphan, expired lock, retry |
| Heartbeat integration | 2 | telemetry, offline detection |
| Boundary invariants | 8 | no cells/environments/subprocess/shell imports |
| Regression | 5 | store backward compat, lifecycle, poller |
| **Total** | **61** | |

---

## Regression

Full suite: 538 tests across phases 11B–17. Zero failures.

| Phase | Tests | Result |
|-------|-------|--------|
| 11B–11F | 259 | PASS |
| 12 | 49 | PASS |
| 13 | 55 | PASS |
| 14 | 50 | PASS |
| 15 | 17 | PASS |
| 16 | 47 | PASS |
| 17 | 61 | PASS |
| **Total** | **538** | **PASS** |

---

## Known Limitations

- No queue prioritization (FIFO by submitted_at only)
- No distributed consensus (single-process lock manager)
- In-memory locking (not file-backed like job persistence)
- No streaming logs from remote workers
- No multi-region awareness
- Daemon tick model (not threaded event loop) — production usage needs caller-driven loop
- Executor callback is synchronous — async execution not yet supported

---

## Files Created/Modified

| File | Action |
|------|--------|
| `umh/jobs/locking.py` | CREATED — 170 lines |
| `umh/jobs/store.py` | MODIFIED — added claim_job(), lock_manager param |
| `umh/nodes/worker.py` | CREATED — 155 lines |
| `umh/nodes/daemon.py` | CREATED — 180 lines |
| `umh/runtime/distributor.py` | CREATED — 90 lines |
| `umh/jobs/__init__.py` | MODIFIED — added JobLock, JobLockManager exports |
| `umh/nodes/__init__.py` | MODIFIED — added daemon, worker exports |
| `umh/runtime/__init__.py` | MODIFIED — added Distributor export |
| `tests/unit/test_phase17_distributed_workers.py` | CREATED — 61 tests |
| `docs/audits/phase17_distributed_workers_report.md` | CREATED — this file |

---

## Is Phase 18 Safe?

YES. Phase 17 is fully backward compatible:
- `JobStore` accepts optional `lock_manager` (default None)
- `RuntimeLoop` was not modified
- All prior phase tests pass unchanged
- New modules add functionality without touching existing modules
