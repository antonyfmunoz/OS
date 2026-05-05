# Phase 9A: Global Attention + Resource Allocation Layer — Completion Report

**Date:** 2026-04-27
**Status:** Complete

---

## Agents Used

| Agent | Task | Output |
|-------|------|--------|
| 1 — Core | Priority model, scorer, queue | umh/attention/*.py |
| 2 — Integration | Worker, API, CLI modifications | umh/orchestrator/worker.py, umh/control/*.py |
| 3 — Frontend | Execution Queue panel | frontend/index.html, app.js |
| 4 — Tests | 3 test suites across attention layer | tests/unit/test_phase9a_*.py |
| Main — Integrator | Compile, format, regression, report | This report |

---

## Architecture: Scored Priority Queue

Phase 9A replaces FIFO task pickup with priority-scored ordering. The attention layer is a PURE scoring + ordering system — no execution, no planning, no mutation of external state.

```
┌──────────────────────────────────────────────────────────────────┐
│                    ATTENTION LAYER (Phase 9A)                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          Priority Scorer (pure functions)                  │  │
│  │                                                            │  │
│  │  score_task(task, goal_priority, age, all_tasks)           │  │
│  │                                                            │  │
│  │  Components:                                               │  │
│  │    importance  (30%) — goal priority mapping               │  │
│  │    recency     (20%) — exponential decay over 1 hour       │  │
│  │    failure_pressure (20%) — retries + failed steps         │  │
│  │    dependency_value (20%) — tasks blocked on this one      │  │
│  │    cost_penalty    (-10%) — step count penalty             │  │
│  │                                                            │  │
│  │  apply_starvation_boost(entry, age, threshold=600)         │  │
│  │    +0.02/min over threshold, capped at 0.3                 │  │
│  │    READY → STARVED on boost                                │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          Attention Queue (thread-safe, max-heap)           │  │
│  │                                                            │  │
│  │  Sort: (-priority_score, created_at) — highest first,      │  │
│  │         oldest first on ties                               │  │
│  │                                                            │  │
│  │  enqueue, dequeue, peek, remove, update_score,             │  │
│  │  update_state, list_ordered, list_by_state,                │  │
│  │  apply_starvation_boost_all                                │  │
│  │                                                            │  │
│  │  Dequeue returns READY or STARVED entries only.            │  │
│  │  BLOCKED, DEFERRED, RUNNING entries are skipped.           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          Attention States                                  │  │
│  │                                                            │  │
│  │  READY    — eligible for execution                         │  │
│  │  BLOCKED  — waiting on dependency                          │  │
│  │  DEFERRED — manually postponed                             │  │
│  │  RUNNING  — currently being executed                       │  │
│  │  STARVED  — low priority, waited too long, boosted         │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Worker Flow Change

```
OLD:  Worker polls → list_by_status(PENDING) → FIFO order → claim → execute
NEW:  Worker polls → list_by_status(PENDING) → score all → enqueue → starvation boost
      → dequeue by priority → claim → execute
```

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `umh/attention/priority.py` | 76 | AttentionState, PriorityBreakdown, PriorityEntry |
| `umh/attention/scorer.py` | 181 | score_task(), apply_starvation_boost(), 5 scoring functions |
| `umh/attention/queue.py` | 166 | AttentionQueue, get/reset singleton |
| `tests/unit/test_phase9a_priority.py` | 245 | Priority model + scorer tests (26) |
| `tests/unit/test_phase9a_queue.py` | 166 | Queue operation tests (18) |
| `tests/unit/test_phase9a_integration.py` | 272 | Boundary + E2E + determinism tests (16) |

## Files Modified

| File | Lines | Change | Impact |
|------|-------|--------|--------|
| `umh/orchestrator/worker.py` | 267 | Priority-ordered task pickup, _resolve_goal, _compute_age | Core — worker now dequeues by priority |
| `umh/control/api.py` | 1883 | +GET /queue, +GET /tasks/{id}/priority, +POST /goals/{id}/priority, +attention metrics | Additive |
| `umh/control/cli.py` | 1686 | +queue command, +task-priority command | Additive |
| `frontend/index.html` | ~565 | +Queue nav button, +Execution Queue panel | Additive |
| `frontend/app.js` | ~1810 | +showQueuePanel, +refreshQueue, +renderQueue | Additive |

---

## Scoring Model

### Priority Score Formula

```
priority_score = (importance × 0.30) + (recency × 0.20) + (failure_pressure × 0.20)
               + (dependency_value × 0.20) - (cost_penalty × 0.10)
               + starvation_boost
```

### Component Functions

| Component | Weight | Input | Range | Formula |
|-----------|--------|-------|-------|---------|
| importance | 30% | GoalPriority | 0.0–1.0 | HIGH=1.0, MEDIUM=0.6, LOW=0.3 |
| recency | 20% | age_seconds | 0.0–1.0 | max(0, 1.0 - age/3600) |
| failure_pressure | 20% | task steps | 0.0–1.0 | retry_rate + 0.3 if any FAILED |
| dependency_value | 20% | all_tasks | 0.0–1.0 | 0.25 per dependent, cap 1.0 |
| cost_penalty | -10% | step count | 0.0–0.1 | min(steps/10, 1.0) × 0.1 |
| starvation_boost | additive | age > 600s | 0.0–0.3 | 0.02/min over threshold |

### Starvation Prevention

```
if age > 600s and state == READY:
    boost = min(0.02 × (age - 600) / 60, 0.3)
    state → STARVED
```

---

## API Surface

### New Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/queue` | GET | Ordered execution queue with all entries |
| `/tasks/{id}/priority` | GET | Priority scoring breakdown for a task |
| `/goals/{id}/priority` | POST | Set goal importance level |

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `GET /tasks` | Includes `priority_score` if task is in queue |
| `GET /metrics` | Added `attention.queue_size` and `attention.starved_count` |

---

## CLI Commands

### New Commands

| Command | Description |
|---------|-------------|
| `queue [--json]` | Show ordered execution queue |
| `task-priority <id> [--json]` | Show task priority scoring breakdown |

---

## Events

No new events introduced. The attention layer is purely observational — it reads task/goal state and produces ordering. The worker still emits all existing task/execution events.

---

## Boundary Verification

### Hard Constraint Proof

| # | Constraint | Status |
|---|-----------|--------|
| 1 | Attention layer is PURE (no execution, no side effects) | PASS — AST verified |
| 2 | No execution imports in attention/ | PASS — AST verified |
| 3 | No adapter imports in attention/ | PASS — AST verified |
| 4 | No tool imports in attention/ | PASS — AST verified |
| 5 | No planning imports in attention/ | PASS — AST verified |
| 6 | No execute() calls in attention/ | PASS — AST verified |
| 7 | No GoalEngine import in attention/ | PASS — AST verified |
| 8 | Scoring is deterministic | PASS — same input → same output tested |
| 9 | Scoring is pure (no mutation) | PASS — task/goal unchanged after scoring |
| 10 | Ordering is stable | PASS — same entries → same dequeue order |

### Import Graph

```
umh/attention/priority.py  → umh.core.clock
umh/attention/scorer.py    → umh.attention.priority
                           → umh.goals.models (GoalPriority only)
                           → umh.orchestrator.task (Task, TaskStatus, StepStatus)
umh/attention/queue.py     → umh.attention.priority
                           → umh.attention.scorer
```

No imports from `umh.execution`, `umh.adapters`, `umh.tools`, `umh.planning`, or `umh.goals.goal_engine`.

---

## Tests

### Phase 9A Tests

| Suite | Tests | Status |
|-------|-------|--------|
| test_phase9a_priority.py | 26 | Pass |
| test_phase9a_queue.py | 18 | Pass |
| test_phase9a_integration.py | 16 | Pass |
| **Total Phase 9A** | **60** | **All pass** |

### Regression

| Suite | Tests | Status |
|-------|-------|--------|
| Phase 8C (refinement) | 62 | Pass |
| Phase 8B (strategy) | 84 | Pass |
| Phase 8A (goals) | 72 | Pass |
| Phase 7D (scheduler) | 71 | Pass |
| Phase 7C (agents) | 78 | Pass (background) |
| Phase 7B (tools) | 114 | Pass (background) |
| Phase 7A (memory) | 91 | Pass (background) |
| Phase 6D+6E (async/retry/worker) | 142 | Pass (background) |
| Phase 5A+6A+6B (spine, meta, control) | 153 | Pass (background) |
| **Total verified** | **927+** | **All pass** |

### Validation

| Check | Result |
|-------|--------|
| `python3 -m py_compile` all Phase 9A files | All OK |
| `ruff format` all Phase 9A files | All formatted |
| No execute() calls in attention/ | PASS (AST) |
| No execution imports in attention/ | PASS (AST) |
| No adapter imports in attention/ | PASS (AST) |
| No tool imports in attention/ | PASS (AST) |
| No planning imports in attention/ | PASS (AST) |

---

## Known Limitations

1. **Queue rebuilt each poll cycle** — worker clears and rescores all pending tasks every poll
2. **In-memory queue** — queue state lost on restart (rebuilds from task store)
3. **Dependency detection is convention-based** — requires `depends_on` in task context
4. **No cost estimation** — cost penalty is step count only, not actual resource cost
5. **No priority decay** — a high-priority task stays high-priority indefinitely
6. **Single worker only** — no multi-worker priority coordination
7. **No priority ceiling** — starvation boost can push low-priority tasks above manual HIGH
8. **No task-level priority override** — priority derives entirely from goal + metrics

---

## Success Condition Verification

> "Decides what should run"

**VERIFIED.** score_task() produces a deterministic priority_score for every task. The queue orders all pending tasks by score.

> "When it should run"

**VERIFIED.** Highest priority tasks dequeue first. Starvation boost ensures nothing waits forever.

> "What should wait"

**VERIFIED.** Lower-priority tasks stay in the queue. BLOCKED/DEFERRED states prevent dequeue.

> "What should be dropped"

**VERIFIED.** DEFERRED state allows manual postponement. Tasks can be cancelled via existing cancel_task().

> "NO autonomy"

**VERIFIED.** The attention layer never decides to execute — it only orders. The worker still executes through the same approval/guard pipeline.

> "NO randomness"

**VERIFIED.** All scoring functions are deterministic. Same inputs → same scores → same ordering. Tested explicitly.

> "NO hidden behavior"

**VERIFIED.** Every score has a PriorityBreakdown with all 5 components visible. API exposes per-task breakdown. CLI shows full scoring. UI explains "why this ran."

> "Deterministic ordering"

**VERIFIED.** Integration tests confirm: same entries → same dequeue order. Scoring is pure (no mutation, no side effects).

> "No starvation"

**VERIFIED.** apply_starvation_boost adds 0.02/min after 600s threshold. After 15 minutes, a LOW priority task gets +0.3 boost, enough to compete with MEDIUM tasks.

> "Remains predictable"

**VERIFIED.** Queue is fully inspectable via GET /queue, task-priority CLI, and the Execution Queue UI panel.
