# Phase 6E: State Consistency Audit
Date: 2026-04-27

## Executive Summary

The UMH task system uses a dual-write model: every `_save_task()` writes to both an in-memory `_tasks` dict and a pluggable `TaskStore` (SQLite in production, InMemory in tests). The in-memory dict acts as a hot cache with SQLite as the durable fallback. This is MVP-safe for a single-process deployment but introduces five concrete divergence risks and one data-loss bug (retry_count deserialization) that must be fixed before any multi-process or crash-recovery scenario.

## Source of Truth Analysis

**There is no single source of truth.** The system operates on a "write both, read memory first" model.

### Write path (`_save_task`, task.py:688-696)
```
_save_task(task):
    1. _tasks[task.id] = task         (in-memory, always succeeds)
    2. get_task_store().save(task)     (SQLite, wrapped in try/except pass)
```
The SQLite write is **fire-and-forget**: if it throws, the exception is silently swallowed (task.py:695-696). The in-memory dict becomes the only record.

### Read path (`get_task`, task.py:699-709)
```
get_task(task_id):
    1. Check _tasks dict first         (in-memory)
    2. If None, fallback to store.get() (SQLite)
```
In-memory always wins. SQLite is only consulted when in-memory has no entry.

### List path (`list_tasks`, task.py:712-719)
```
list_tasks():
    1. Try store.list_all()            (SQLite)
    2. On exception, fallback to _tasks.values()
```
**Inverted priority**: listing prefers SQLite, individual gets prefer in-memory. This asymmetry can produce contradictory results.

### Find paused (`find_paused_task_by_approval`, task.py:722-736)
```
find_paused_task_by_approval(approval_id):
    1. Scan _tasks dict for matching PAUSED task
    2. If not found, scan store.list_by_status(PAUSED)
```
Searches both, in-memory first. Could return a stale in-memory task that SQLite has already moved past PAUSED.

## In-Memory State Usage

Every reference to `_tasks` dict (module-level `dict[str, Task]` at task.py:684):

| Location | Operation | Description |
|---|---|---|
| task.py:684 | declaration | `_tasks: dict[str, Task] = {}` |
| task.py:685 | declaration | `_tasks_lock = threading.Lock()` |
| task.py:689-690 | write | `_save_task()` → `_tasks[task.id] = task` |
| task.py:700-701 | read | `get_task()` → `_tasks.get(task_id)` — **primary read** |
| task.py:718-719 | read | `list_tasks()` fallback — only if SQLite throws |
| task.py:724-726 | read | `find_paused_task_by_approval()` — scans `_tasks.values()` first |
| task.py:740-741 | delete | `reset_tasks()` → `_tasks.clear()` |

**Who calls these:**
- `get_task()`: api.py:453, api.py:468, api.py:492, api.py:512, api.py:534, cli.py:142, cli.py:241, task.py:381, task.py:604, task.py:642, engine.py:231 (via find_paused), timeline.py:20
- `list_tasks()`: api.py:231 (metrics), api.py:392 (GET /tasks), cli.py:161
- `find_paused_task_by_approval()`: engine.py:231 (orchestrator rule for auto-resume)

## SQLite State Usage

Every reference to `task_store` / `get_task_store()`:

| Location | Operation | Description |
|---|---|---|
| task.py:692-694 | write | `_save_task()` → `get_task_store().save(task)` — **secondary write** |
| task.py:705-707 | read | `get_task()` fallback — only if `_tasks` miss |
| task.py:714-716 | read | `list_tasks()` — **primary list** |
| task.py:729-733 | read | `find_paused_task_by_approval()` — secondary scan |
| task.py:743-745 | delete | `reset_tasks()` → `get_task_store().reset()` |
| worker.py:99 | read | Worker polls `store.list_by_status(PENDING)` |
| worker.py:107-110 | write | Worker calls `store.claim_task()` |
| worker.py:117 | read | Worker calls `store.get()` for fresh copy |
| worker.py:124 | write | Worker calls `store.save(result)` after execution |
| worker.py:132-134 | read+write | Worker calls `store.list_stuck_tasks()` and `store.recover_stuck_task()` |
| worker.py:137-146 | read+write | Worker finds resumable tasks via store, then calls `resume_task()` |

**Critical observation**: The worker operates primarily through the SQLite store directly, bypassing the in-memory `_tasks` dict for reads. But `execute_task()` and `resume_task()` internally call `_save_task()` which writes to BOTH.

## Divergence Risk Analysis

### Risk 1: Silent SQLite write failure (CRITICAL)

**File**: task.py:691-696
```python
def _save_task(task: Task) -> None:
    with _tasks_lock:
        _tasks[task.id] = task
    try:
        get_task_store().save(task)
    except Exception:
        pass  # ← silent swallow
```

**Scenario**: SQLite disk full, file locked, or schema migration failure. In-memory has the task, SQLite does not. After process restart, task is lost.

**Impact**: HIGH. Any task that only exists in memory vanishes on restart. The `except Exception: pass` means no logging, no alerting, no retry.

### Risk 2: Worker reads store, execute_task reads memory (MEDIUM)

**Flow**:
1. Worker calls `store.list_by_status(PENDING)` → gets task from SQLite (worker.py:105)
2. Worker calls `store.claim_task()` → updates SQLite to RUNNING (worker.py:110)
3. Worker calls `store.get()` → gets fresh task from SQLite (worker.py:117)
4. Worker sets `fresh.status = RUNNING` on the **new Task object** from SQLite (worker.py:121)
5. Worker calls `execute_task(fresh)` → this writes to both _tasks AND store (task.py:688-696)
6. Worker calls `store.save(result)` → **double-writes** to SQLite again (worker.py:124)

The worker's `store.save(result)` at step 6 is redundant — `execute_task()` already called `_save_task()` which wrote to SQLite. This is harmless (idempotent upsert via INSERT OR REPLACE) but wasteful.

**Divergence**: The Task object in `_tasks` is the **same object reference** passed through `execute_task()`. The Task object in SQLite is a **serialized/deserialized copy**. Any mutable state not captured by `to_dict()` / `_row_to_task()` will diverge.

### Risk 3: retry_count data loss on deserialization (BUG)

**File**: task_store.py:198-207

The `_row_to_task()` method creates TaskSteps without restoring `retry_count`:
```python
step = TaskStep(
    operation=sd["operation"],
    ...
    result=sd.get("result"),
    # retry_count is MISSING — defaults to 0
)
```

The `retry_count` IS serialized by `TaskStep.to_dict()` (task.py:76) and stored in `steps_json`. But deserialization never reads it back. Any task loaded from SQLite will have `retry_count=0` on all steps, regardless of actual retry history.

**Impact**: MEDIUM. Incorrect retry counts after process restart. Could cause retry loops if retry limits are ever enforced.

### Risk 4: list_tasks vs get_task priority inversion (LOW)

- `get_task()` reads **in-memory first**, SQLite fallback
- `list_tasks()` reads **SQLite first**, in-memory fallback

A caller who does `list_tasks()` then `get_task(id)` on the same task could see **different versions** if in-memory and SQLite have diverged (e.g., due to Risk 1).

**Impact**: LOW for MVP (single process, divergence unlikely unless disk error). Would surface as confusing API behavior: GET /tasks shows one status, GET /tasks/{id} shows another.

### Risk 5: find_paused_task_by_approval scans both (LOW)

**File**: task.py:722-736

The function scans `_tasks` dict first, then falls through to SQLite. If the in-memory copy is stale (e.g., task was resumed by another code path that only updated SQLite), this function returns the stale PAUSED version. The orchestrator rule (engine.py:231) then calls `resume_task()` on an already-resumed task.

`resume_task()` does check `task.status != TaskStatus.PAUSED` (task.py:386-387), so this is a failed-resume with a log warning, not a double-execution. But it's unnecessary noise.

## Critical Path Inventory

Ordered by severity of inconsistency impact:

| Priority | Path | Read Source | Write Target | Risk |
|---|---|---|---|---|
| P0 | Worker polling + claim | SQLite only | SQLite (claim_task) | Claim skips in-memory entirely. In-memory _tasks has stale status after claim. |
| P0 | execute_task / resume_task | In-memory (via _save_task) | Both (dual-write) | Silent SQLite failure = data loss on restart |
| P1 | GET /tasks/{id} | In-memory first | N/A (read-only) | Returns stale in-memory if SQLite updated externally |
| P1 | GET /tasks (list) | SQLite first | N/A (read-only) | Inconsistent priority vs get_task |
| P2 | Orchestrator auto-resume | In-memory first, then SQLite | Both (via resume_task) | Could attempt resume on stale PAUSED task |
| P2 | Metrics (_task_metrics) | Via list_tasks → SQLite | N/A | Correct for SQLite, could show stale fallback |

## Dual-Write Safety Assessment

### Safe for MVP: YES, with caveats

**Why it works for MVP:**
1. Single-process deployment — in-memory and SQLite are always updated from the same thread (protected by `_tasks_lock`)
2. The worker is the only concurrent accessor, and it reads from SQLite directly
3. SQLite uses WAL mode and `busy_timeout=3000` for write contention
4. `claim_task` uses atomic SQL UPDATE with WHERE clause — no double-execution possible via SQLite

**Failure modes that exist:**
1. **Silent SQLite failure** (Risk 1): The `except Exception: pass` in `_save_task()` means any SQLite error is invisible. Process restart loses all tasks that failed to persist.
2. **In-memory cache stale after claim**: When the worker calls `store.claim_task()`, it updates SQLite status to RUNNING but does NOT update `_tasks` dict. If an API call hits `get_task()` between claim and `_save_task()`, it sees the old PENDING status from `_tasks`.
3. **Object identity divergence**: The worker creates a new Task object from `store.get()` (worker.py:117). This is a different Python object than what's in `_tasks`. Mutations to one do not affect the other until the next `_save_task()`.
4. **retry_count loss** (Risk 3): Active bug. Any task loaded from SQLite loses step retry counts.

### Not safe for:
- Multi-process workers (claim_task is per-backend atomic, but in-memory dict is process-local)
- Crash recovery expectations (silent SQLite failures are undetected)
- Systems that rely on retry_count accuracy

## Future Cutover Plan

Step-by-step to make SQLite the sole source of truth and remove the in-memory `_tasks` dict:

### Phase 1: Fix existing bugs (before cutover)
1. **Fix retry_count deserialization** in `task_store.py:_row_to_task()`: add `retry_count=sd.get("retry_count", 0)` to the TaskStep constructor call.
2. **Add logging to SQLite write failures**: Replace `except Exception: pass` with `except Exception: _log.error("SQLite save failed for task %s", task.id, exc_info=True)`.

### Phase 2: Make SQLite authoritative for reads
3. **Invert `get_task()` priority**: Read from SQLite first, fall back to in-memory.
   ```python
   def get_task(task_id: str) -> Task | None:
       try:
           task = get_task_store().get(task_id)
           if task is not None:
               return task
       except Exception:
           pass
       with _tasks_lock:
           return _tasks.get(task_id)
   ```
4. **Align `find_paused_task_by_approval()`**: Search SQLite first, in-memory fallback.
5. **Verify**: All tests still pass. API returns consistent results.

### Phase 3: Make in-memory a write-through cache
6. **In `_save_task()`**: Write to SQLite FIRST. If it succeeds, update in-memory. If it fails, log and still update in-memory (graceful degradation).
   ```python
   def _save_task(task: Task) -> None:
       try:
           get_task_store().save(task)
       except Exception:
           _log.error("SQLite save failed for task %s", task.id, exc_info=True)
       with _tasks_lock:
           _tasks[task.id] = task
   ```

### Phase 4: Remove in-memory dict
7. **Remove `_tasks` dict, `_tasks_lock`** (task.py:684-685).
8. **Rewrite `get_task()`** to call `get_task_store().get()` directly.
9. **Rewrite `list_tasks()`** — remove fallback.
10. **Rewrite `find_paused_task_by_approval()`** — remove in-memory scan.
11. **Rewrite `reset_tasks()`** — remove `_tasks.clear()`.
12. **Rewrite `_save_task()`** — only call `get_task_store().save()`, no silent swallow.

### Phase 5: Verify
13. Run full test suite. Specifically verify:
    - Worker claim → execute → save round-trip
    - Restart simulation (clear process, reload from SQLite)
    - Paused task resume after process restart
    - API consistency: GET /tasks and GET /tasks/{id} return same status
14. Load test: concurrent worker polls with SQLite as sole backend.

## Test Coverage Gaps

### What IS tested (test_phase6d_async_runtime.py, test_phase5e.py):
- Task store persistence: save, get, list_all, list_by_status (InMemoryTaskBackend)
- claim_task atomicity: double-claim fails, concurrent claims (InMemoryTaskBackend)
- Restart simulation: clear `_tasks` dict, verify SQLite still has data
- Worker poll cycle: picks up PENDING, executes, saves
- API endpoints: POST/GET/resume/cancel/retry tasks

### What IS tested (test_phase6e_worker_recovery.py):
- list_stuck_tasks finds expired tasks
- recover_stuck_task marks FAILED
- Worker recovery loop integration

### What is NOT tested:

| Gap | Risk | Description |
|---|---|---|
| Silent SQLite write failure | HIGH | No test verifies behavior when `get_task_store().save()` throws inside `_save_task()`. The `except Exception: pass` is untested. |
| In-memory/SQLite divergence | HIGH | No test where in-memory and SQLite have different task states, then verifies which one wins. |
| retry_count round-trip | MEDIUM | No test serializes a TaskStep with `retry_count > 0` to SQLite and deserializes it back. Would catch the active bug. |
| list_tasks vs get_task consistency | LOW | No test calls both and asserts they return the same status for the same task. |
| SQLiteTaskBackend in production config | MEDIUM | All tests use `UMH_TASK_BACKEND=memory` or `InMemoryTaskBackend()`. No test exercises `SQLiteTaskBackend` directly (claim_task atomicity, WAL mode, busy_timeout). |
| claim_task in-memory cache staleness | MEDIUM | No test verifies that `get_task()` returns correct status between `store.claim_task()` and `execute_task()`. |
| find_paused_task_by_approval with stale in-memory | LOW | No test where in-memory shows PAUSED but SQLite shows COMPLETED. |
| Worker double-write redundancy | LOW | No test verifies `store.save(result)` after `execute_task()` is idempotent (it is, but untested). |

## Recommendations

1. **Fix retry_count deserialization NOW** — This is an active bug. Add `retry_count=sd.get("retry_count", 0)` to `_row_to_task()` in task_store.py:198-207.

2. **Replace `except Exception: pass` with logging** — The silent swallow in `_save_task()` (task.py:695-696) is the single highest-risk line in the task system. At minimum log the error. Consider failing the task if SQLite is unreachable.

3. **Add a SQLiteTaskBackend integration test** — The entire test suite runs against InMemoryTaskBackend. One test class should use a temp SQLite file to verify claim_task atomicity, WAL mode behavior, and schema migration.

4. **Add a divergence test** — Explicitly break SQLite (e.g., mock it to throw), verify in-memory still works, then verify the logged error. This validates graceful degradation.

5. **Do NOT rush the cutover** — The dual-write model is ugly but functional for single-process MVP. The bugs above (retry_count, silent swallow) should be fixed first. The cutover (Phases 2-4 above) can happen when multi-process workers or crash recovery becomes a real requirement.

6. **Track the worker double-write** — worker.py:124 (`store.save(result)`) is redundant with `_save_task()` inside `execute_task()`. Not harmful but should be removed when `_save_task()` is made reliable (i.e., SQLite errors are not silenced).
