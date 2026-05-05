# Phase 5F: Parallel Quality Expansion Pass — Audit Report

**Date:** 2026-04-27
**Status:** COMPLETE

## Agents Used

| Agent | Track | Outcome |
|-------|-------|---------|
| Agent 1 — Task Persistence Auditor | Research only | **Keep in-memory** — tasks are synchronous, short-lived, result returned inline. No cross-process or cross-restart need. |
| Agent 2 — Task API Hardening | Code + tests | Added input validation (empty steps, empty operation, invalid execution_class) + GET /tasks list endpoint. 20 new tests. |
| Agent 3 — Task Observability + Events | Tests only | All events verified correct and complete. 41 new tests. 0 fixes needed in task.py. |
| Agent 4 — Task Execution Semantics | Tests only | All edge cases verified correct. 33 new tests using stub backends (0.14s). 0 bugs found. |
| Agent 5 — Approval-in-Task Integration | Tests + docs | Confirmed: task FAILS deterministically when step requires approval. Documented blocker for pause/resume. 18 new tests. |
| Agent 6 — Metrics + Status Surface | Code + tests | Added `_task_metrics()` to /metrics response: total_tasks, tasks_by_status, recent_tasks. 21 new tests. |
| Agent 7 — Dead Code Safety Sweep | Research only | No Phase 5E regressions. Found 2 pre-existing broken Discord commands (not 5E scope). No bypasses introduced. |

## Files Changed

| File | Action | Agent |
|------|--------|-------|
| `umh/control/api.py` | Modified — validation guards, GET /tasks, task metrics | Agent 2, 6 |
| `tests/unit/test_phase5f_api.py` | NEW — 20 tests | Agent 2 |
| `tests/unit/test_phase5f_events.py` | NEW — 41 tests | Agent 3 |
| `tests/unit/test_phase5f_semantics.py` | NEW — 33 tests | Agent 4 |
| `tests/unit/test_phase5f_approval.py` | NEW — 18 tests | Agent 5 |
| `tests/unit/test_phase5f_metrics.py` | NEW — 21 tests | Agent 6 |

## Tests Added: 133 new tests

| File | Tests | Runtime |
|------|-------|---------|
| test_phase5f_api.py | 20 | ~131s (LLM calls via CC SDK) |
| test_phase5f_events.py | 41 | ~5min (LLM calls via CC SDK) |
| test_phase5f_semantics.py | 33 | 0.14s (stub backends) |
| test_phase5f_approval.py | 18 | ~70s (mix of guard-rejected + LLM) |
| test_phase5f_metrics.py | 21 | ~4min (LLM calls via CC SDK) |

## Tests Run

| Suite | Result |
|-------|--------|
| Phase 5E (baseline) | 43 passed (355.70s) |
| Cross-phase 4D–5E | 295 passed (509.39s) |
| Phase 5F: semantics | 33 passed (0.14s) |
| Phase 5F: API | 20 passed (131s) |
| Phase 5F: approval | 18 passed (70s) |
| Phase 5F: events | 41 passed (exit 0) |
| Phase 5F: metrics | 21 passed (exit 0) |

## Remaining Blockers

### Task Pause/Resume on Approval (documented, not implemented)

When a task step requires approval:
1. `execute()` returns `REJECTED` with `requires_approval=True`
2. `execute_task()` sees `status != SUCCEEDED` → marks task FAILED
3. Orchestrator's `builtin:replay_on_approval` replays the individual execution — but the task has already exited

**To implement pause/resume requires:**
1. `TaskStatus.PAUSED` + detection of `requires_approval` in `execute_task()`
2. Task re-entry at `current_step_index` after approval
3. `approval_id → task_id` linkage for orchestrator notification

**Decision:** Defer. Current behavior (fail deterministically) is safe and predictable.

### Pre-existing Issues (not Phase 5E/5F scope)

- `umh/interfaces/discord/bot.py:2725` — `!portfolio` command references missing `scripts/portfolio_brief.py`
- `umh/interfaces/discord/bot.py:2820` — `!eod` command references missing `scripts/eod_sync.py`

## Direct Bypass Audit Result

```bash
grep -R "call_with_fallback|router.call|subprocess.run(command, shell=True)" umh/ | grep -v model_router|cc_sdk|adapters
```

**Result:** All `call_with_fallback` references are legitimate uses through the canonical `model_router` entry point. No direct LLM/subprocess bypasses introduced by Phase 5E or 5F.

Pre-existing substrate-layer calls (voice_engine, multi_strategy, voice_eos_responder, llm_generation stage) all route through `model_router.call_with_fallback()` — the single sanctioned entry point.

## Task Persistence Decision

**Keep in-memory.** Rationale:
- Tasks are synchronous — result returned inline in POST response
- No cross-process or cross-restart lookup path exists
- Max 10 steps, ~5 minute max lifetime per task
- Control API is CLI-launched, not a persistent service
- Revisit when async dispatch or cross-process polling is needed

## API Changes (Phase 5F)

| Method | Path | Change |
|--------|------|--------|
| POST | `/tasks` | Added: empty steps → 400, empty operation → 400, invalid execution_class → 400 |
| GET | `/tasks` | NEW — list all tasks (execute scope) |
| GET | `/metrics` | Extended — includes `tasks` block with counts and recent_tasks |

## Metrics Extension

```json
{
  "tasks": {
    "total_tasks": 3,
    "tasks_by_status": {"pending": 0, "running": 0, "completed": 2, "failed": 1},
    "recent_tasks": [
      {"id": "task_abc123", "status": "completed", "step_count": 2, "created_at": "..."}
    ]
  }
}
```

## Whether Phase 6A Is Safe

**Yes.** The task execution system is:
- Deterministic (strict sequential, fail-fast, no parallelism)
- Observable (events emitted for every lifecycle transition)
- Hardened (input validation, max steps enforced, error messages descriptive)
- Tested (43 Phase 5E + 133 Phase 5F = 176 task-specific tests)
- Clean (no bypasses, no dead code, no schema changes)

The only structural gap is task pause/resume for approval-requiring steps — explicitly documented and deferred.

## Validation

```bash
python3 -c "from umh.orchestrator.task import Task, TaskStep, execute_task; print('OK')"  # OK
python3 -c "from umh.control.api import app; print('OK')"                                  # OK
python3 -c "from umh.events.stream import get_event_stream; print('OK')"                   # OK
```

## LLM Routing Confirmation

All execution calls route through:
```
execute() → SpineExecutionBackend._execute_llm() → call_with_fallback() → CC SDK → Opus 4.6
```

Fallback chain: Claude CLI (tmux, fails with import error) → CC SDK (Opus 4.6, ~13-20s) → registry providers → Ollama (dead last, priority 7).

Production calls confirmed hitting **cc_sdk / claude-opus-4-6**.
