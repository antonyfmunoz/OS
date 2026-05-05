# Phase 15 — Asynchronous Distributed Execution Jobs + Remote Job Lifecycle v1

**Date:** 2026-04-30
**Status:** COMPLETE
**Tests:** 66 passed (Phase 15) + 364 passed (11B-14 regression)

---

## What Changed After Phase 14

Phase 14 provided a real SSH transport boundary for synchronous remote
command execution. Phase 15 adds a lifecycle layer on top: jobs are
explicitly tracked, cancellable, timeout-aware, and orphan-detectable.

New package: `umh/jobs/` (4 modules)

## Job Lifecycle Model

### ExecutionJob

Tracked unit of distributed work:
- `job_id`, `task_id`, `node_id`
- `status` (JobStatus enum)
- `command` (list[str] or None)
- Timestamps: `created_at`, `submitted_at`, `started_at`, `finished_at`, `last_poll_at`
- `timeout_seconds` (default 60)
- `attempts`, `max_attempts` (retry control)
- `result`, `error`, `metadata`

### JobStatus Enum

```
CREATED → SUBMITTED → RUNNING → SUCCEEDED
                   ↘ FAILED    ↗
                   ↘ CANCELLED
                        RUNNING → TIMEOUT
                        RUNNING → ORPHANED
                        RUNNING → CANCELLED
```

### State Transition Diagram

```
CREATED ──→ SUBMITTED ──→ RUNNING ──→ SUCCEEDED (terminal)
                 │              │
                 ├──→ FAILED    ├──→ FAILED
                 │              ├──→ TIMEOUT
                 └──→ CANCELLED ├──→ CANCELLED (terminal)
                                └──→ ORPHANED

FAILED ──→ SUBMITTED   (if attempts < max_attempts)
TIMEOUT ──→ SUBMITTED  (if attempts < max_attempts)
ORPHANED ──→ SUBMITTED (if attempts < max_attempts)
```

Terminal states:
- SUCCEEDED (always terminal)
- CANCELLED (always terminal)
- FAILED, TIMEOUT, ORPHANED (terminal when attempts >= max_attempts)

### Lifecycle Functions

- `can_transition(from, to)` — validates transition
- `transition(job, new_status)` — applies transition, updates timestamps/attempts
- `is_terminal(status)` — checks always-terminal states
- `is_terminal_for_job(job)` — checks terminal considering retry exhaustion
- `should_retry(job)` — checks if retry is possible

All transitions go through `lifecycle.transition()`. Direct status
assignment is never used by the store or poller.

## In-Memory Job Store

`umh/jobs/store.py`

- `create_job()` — creates CREATED job with generated ID
- `get_job()` / `list_jobs()` — query by ID, status, or node_id
- `mark_submitted()` / `mark_running()` / `mark_succeeded()` — status updates
- `mark_failed()` / `mark_timeout()` / `mark_orphaned()` / `cancel_job()`
- All mutations go through `lifecycle.transition()` — invalid transitions raise ValueError
- Thread-safe with lock
- In-memory only (no DB backing for Phase 15)

## Remote Client Async Contract

Phase 15 does not add new methods to RemoteNodeClient. The existing
`TransportBackedRemoteNodeClient` from Phase 14 provides:
- `submit_execution()` — synchronous SSH execution, immediate result
- `fetch_result()` — returns stored result
- `cancel()` — marks CANCELLED if not terminal

The JobStore tracks the lifecycle explicitly around these calls.
The transport is synchronous under the hood, but the job lifecycle
provides the async state machine that a future async transport plugs into.

## Polling / Result Collection

`umh/jobs/poller.py`

JobPoller provides three polling operations:

1. **poll_once()** — iterates RUNNING + SUBMITTED jobs, calls
   `remote_client.fetch_result()` for each, applies results to store
2. **detect_timeouts()** — checks elapsed time against timeout_seconds,
   marks RUNNING → TIMEOUT, SUBMITTED → FAILED
3. **detect_orphans()** — checks node health, marks RUNNING → ORPHANED
   when node is OFFLINE

Plus retry support:
- **retry_eligible()** — lists FAILED/TIMEOUT/ORPHANED jobs with retries remaining
- **retry_job()** — transitions eligible job back to SUBMITTED

All operations are non-blocking. Exceptions are caught per-job and
logged, never propagated to crash the caller.

## Timeout / Orphan Detection

Timeout:
- Compares `started_at` (or `submitted_at` or `created_at`) against `timeout_seconds`
- RUNNING jobs that exceed timeout → TIMEOUT
- SUBMITTED jobs that exceed timeout → FAILED (stuck in queue)

Orphan:
- Requires node health map
- RUNNING jobs on OFFLINE nodes → ORPHANED
- Without health data, no orphans are detected (safe default)

Both are deterministic — accept `now` parameter for testing.

## Runtime Loop Integration

`umh/runtime/loop.py` — extended

New optional constructor parameters:
- `job_poller: JobPoller | None`
- `job_store: JobStore | None`

`tick()` now includes `_poll_jobs()`:
1. Calls `detect_timeouts()` on the job store
2. Builds node health map if health manager present
3. Calls `detect_orphans()` with health map
4. Returns `job_updates` dict with `timed_out` and `orphaned` lists
5. Never crashes — wrapped in try/except

Backward compatible: without job_poller/job_store, tick behaves exactly
as Phase 14.

## What Is Real vs Stubbed

| Component | Status |
|-----------|--------|
| Job lifecycle state machine | Real |
| State transition validation | Real |
| In-memory job store | Real |
| Timeout detection | Real |
| Orphan detection | Real |
| Retry logic | Real |
| Runtime loop job polling | Real |
| Remote execution via SSH | Real (synchronous, Phase 14) |
| Durable job persistence | Not implemented (in-memory only) |
| Async remote job daemon | Not implemented |
| Streaming logs | Not implemented |
| Remote Docker job supervisor | Not implemented |

## Invariants Preserved

1. Cells NEVER execute — verified by boundary tests
2. Cells NEVER import environments — verified
3. Cells NEVER import nodes — verified
4. Cells NEVER import transports — verified
5. Cells NEVER import jobs — verified (new)
6. All execution flows through control plane
7. Local subprocess/docker confined to approved layers — verified
8. No shell=True — verified by AST analysis
9. Sandbox always gates before execution — unchanged
10. Remote node failure degrades safely — jobs marked ORPHANED, not crashed
11. Scheduler/router remain pure — unchanged
12. No global mutable state — all state in class instances
13. Async jobs explicitly tracked, cancellable, timeout-aware — verified
14. Orphan jobs detected, never ignored — verified

## Files Created

- `umh/jobs/__init__.py` — package init + exports
- `umh/jobs/models.py` — ExecutionJob, JobResult, JobStatus
- `umh/jobs/lifecycle.py` — state machine transitions
- `umh/jobs/store.py` — in-memory job store
- `umh/jobs/poller.py` — job polling, timeout/orphan detection
- `tests/unit/test_phase15_async_jobs.py` — 66 tests
- `docs/audits/phase15_async_jobs_report.md` — this file

## Files Modified

- `umh/runtime/loop.py` — added optional job_poller/job_store + _poll_jobs()

## Test Summary

| Suite | Tests | Result |
|-------|-------|--------|
| Phase 15 async jobs | 66 | all passed |
| Phase 14 transport | 50 | all passed |
| Phase 13 distributed | 55 | all passed |
| Phase 12 runtime | 44 | all passed |
| Phase 11F execution | 40 | all passed |
| Phase 11E environment | 37 | all passed |
| Phase 11D orchestration | 45 | all passed |
| Phase 11C cells + brain | 54 | all passed |
| Phase 11B brains | 39 | all passed |
| **Total** | **430** | **all passed** |

## Known Limitations

- In-memory JobStore only (no DB persistence)
- SSH jobs are immediate/synchronous under the hood
- No durable distributed job queue
- No streaming logs from remote jobs
- No remote background daemon
- No remote Docker job supervisor
- No mesh/P2P networking
- No parallel multi-node job submission
- No job priority/scheduling beyond retry count
- Poller must be driven externally (no self-scheduling)

## Is Phase 16 Safe?

Yes. Phase 15 adds a clean new `umh/jobs/` package with no cross-contamination:
- `models.py` depends only on `umh/core/clock`
- `lifecycle.py` depends only on models
- `store.py` depends only on lifecycle + models
- `poller.py` depends only on store + lifecycle + models

Phase 16 can safely build:
- DB-backed persistent job store
- Async transport wrapper for non-blocking SSH
- Remote job daemon with background execution
- Job priority and scheduling
- Streaming log collection from remote jobs
- Multi-node parallel job submission
- Job result caching and deduplication
