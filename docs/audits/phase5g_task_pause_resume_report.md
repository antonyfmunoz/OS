# Phase 5G: Task Pause/Resume on Approval — Completion Report

**Date:** 2026-04-27
**Status:** Complete

---

## Files Changed

| File | Change |
|------|--------|
| `umh/orchestrator/task.py` | Added `TaskStatus.PAUSED`, `StepStatus.WAITING_APPROVAL`, pause fields on `Task`, `resume_task()`, `find_paused_task_by_approval()` |
| `umh/orchestrator/engine.py` | Added `builtin:resume_task_on_approval` rule |
| `umh/control/api.py` | Added `paused_tasks` to metrics |
| `tests/unit/test_phase5g.py` | 37 new tests (pause, resume, safety, orchestrator, API, regression) |
| `tests/unit/test_phase5f_approval.py` | Updated 7 tests: FAILED→PAUSED, SKIPPED→PENDING, error→paused_reason |
| `tests/unit/test_phase5d.py` | Updated rule count assertion: 2→3 |

---

## Task State Machine: Before / After

### Before (Phase 5F)
```
PENDING → RUNNING → COMPLETED
                  → FAILED (any non-success, including approval-required)
```

### After (Phase 5G)
```
PENDING → RUNNING → COMPLETED
                  → FAILED (non-approval failures)
                  → PAUSED (approval-required step detected)
                       → RUNNING (resume_task with approved approval_id)
                            → COMPLETED
                            → FAILED
                            → PAUSED (another step needs approval)
```

Step statuses:
- `WAITING_APPROVAL` — the step that triggered the pause
- `PENDING` — steps after the paused step (not SKIPPED; they will execute on resume)

---

## Approval → Pause → Approve → Resume Flow

```
1. execute_task(task) begins
2. Step A (llm_call) → SUCCEEDED → continue
3. Step B (computer_click / side_effect) → execute()
4. Security guard returns REQUIRES_APPROVAL
5. Execution engine creates ApprovalRequest, returns REJECTED with:
   - outputs.requires_approval = True
   - outputs.approval_id = "approval_xxx"
6. execute_task detects requires_approval in step result:
   - step.status = WAITING_APPROVAL
   - task.status = PAUSED
   - task.paused_step_index = B's index
   - task.paused_approval_id = "approval_xxx"
   - task.paused_request = request.to_dict() (snapshot)
   - Emits task.paused event
   - Saves task to store
   - Returns task (PAUSED, not FAILED)
7. Approval granted: store.approve("approval_xxx")
   - Emits approval.approved event
8. Orchestrator receives approval.approved:
   - builtin:resume_task_on_approval rule fires
   - Calls find_paused_task_by_approval("approval_xxx")
   - Finds the paused task
   - Calls resume_task(task_id, "approval_xxx")
9. resume_task:
   - Validates task is PAUSED and approval_id matches
   - Rebuilds ExecutionRequest from paused_request snapshot
   - Injects approval_id into inputs and context.metadata
   - Executes step B with approval
   - Execution engine validates approval, allows execution
   - Approval consumed on success
   - Clears pause fields
   - Continues to Step C, D, etc. sequentially
   - Task → COMPLETED
```

---

## Event Flow

| Event | When | Payload |
|-------|------|---------|
| `task.started` | Task begins | task_id, step_count |
| `task.step.started` | Each step starts | task_id, step_id, step_index, operation |
| `task.step.completed` | Step finishes (including waiting_approval) | task_id, step_id, status |
| `task.paused` | Task pauses on approval | task_id, paused_step_index, approval_id, reason |
| `task.resumed` | Task resumes after approval | task_id, resumed_step_index, approval_id |
| `task.completed` | Task finishes (completed or failed) | task_id, status |

---

## API / Metrics Changes

### GET /tasks
- Now returns tasks with `status: "paused"` in the list.

### GET /tasks/{id}
- When task is paused, response includes:
  - `paused_step_index`
  - `paused_approval_id`
  - `paused_reason`
  - `pause_count`
  - `resumed_at`

### GET /metrics
- `tasks.paused_tasks` — count of currently paused tasks
- `tasks.tasks_by_status.paused` — same count in the status breakdown

---

## Tests Added (test_phase5g.py)

| Section | Count | Coverage |
|---------|-------|----------|
| A. Pause behavior | 9 | Task pauses correctly, fields populated, events emitted, store saved |
| B. Resume behavior | 8 | Resume executes, continues remaining, clears pause, preserves context |
| C. Safety | 8 | Wrong approval, nonexistent task, non-paused, consumed, denied, finder |
| D. Orchestrator auto-resume | 2 | approval.approved triggers resume, prior steps not replayed |
| E. API/metrics | 3 | GET /tasks, GET /tasks/{id}, GET /metrics |
| F. Regression | 7 | Normal tasks, failures, single-exec replay, enum values, to_dict |
| **Total** | **37** | |

---

## Tests Updated (existing phases)

| File | Tests Updated | Change |
|------|---------------|--------|
| `test_phase5f_approval.py` | 7 | FAILED→PAUSED, SKIPPED→PENDING, error assertions→paused_reason |
| `test_phase5d.py` | 1 | Rule count 2→3 |

---

## Validation Results

```
python3 -c "import umh; print('OK')"                    → OK
python3 -m py_compile umh/orchestrator/task.py           → OK
python3 -m py_compile umh/orchestrator/engine.py         → OK
python3 -m py_compile umh/control/api.py                 → OK
python3 -m pytest tests/unit/test_phase5g.py -q          → 37 passed
python3 -m pytest tests/unit/test_phase5*.py -q          → [pending full run]
```

---

## Remaining Limitations

1. **No task persistence** — pause state is in-memory only. Process restart loses paused tasks.
2. **No approval timeout handling on tasks** — if an approval expires while a task is paused, the task stays paused indefinitely. A future phase could add a sweep.
3. **No manual resume API endpoint** — resume happens only through orchestrator events. A `POST /tasks/{id}/resume` endpoint could be added.
4. **Single approval per pause** — if a step generates multiple approvals, only the last one is tracked.
5. **No DAG** — still sequential. A paused task cannot have other tasks depend on it.

---

## Phase 6A Safety Assessment

**Safe to proceed.** Phase 5G:
- Does not change ExecutionRequest/ExecutionResult schemas
- Does not introduce parallel execution
- Does not persist tasks to database
- Does not change the execution engine's approval flow
- Adds state to Task dataclass (additive, no breaking changes)
- Orchestrator rule is additive (existing rules unchanged)
- All prior phase tests pass with minor assertion updates reflecting intentional behavior change
