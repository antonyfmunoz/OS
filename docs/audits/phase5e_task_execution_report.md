# Phase 5E: Multi-Step Execution Graph — Audit Report

**Date:** 2026-04-26
**Status:** COMPLETE

## Files Changed

| File | Action |
|------|--------|
| `umh/orchestrator/task.py` | NEW — Task, TaskStep, execute_task, resolve_inputs, memory store |
| `umh/control/api.py` | Modified — added POST /tasks, GET /tasks/{id} endpoints |
| `tests/unit/test_phase5e.py` | NEW — 43 tests |

## Architecture

```
           POST /tasks
               │
               ▼
        ┌─────────────┐
        │  API Layer   │
        │  (FastAPI)   │
        └──────┬──────┘
               │
               ▼
        ┌─────────────┐
        │    Task      │
        │              │
        │  Steps:      │
        │  ┌──────────────────────────────────┐
        │  │ step 0: classify_intent          │
        │  │   → output_key: "classification" │
        │  │ step 1: respond                  │
        │  │   → inputs: {{context.class...}} │
        │  └──────────────────────────────────┘
        │              │
        │  Context:    │
        │  {output_key → step_result}         │
        └──────┬──────┘
               │
       for each step:
               │
               ▼
        ┌─────────────┐
        │   Engine     │  execute(request)
        │  execute()   │  full pipeline:
        │              │  guard → backend → events
        └──────┬──────┘
               │
               ▼
        ┌─────────────┐
        │  EventStream │  task.started
        │              │  task.step.started
        │              │  task.step.completed
        │              │  task.completed
        └─────────────┘
```

## Flow: Multi-Step Execution

```
1. API receives POST /tasks with steps[] and context{}
   → validates max 10 steps
   → creates Task with TaskSteps
   → calls execute_task(task)

2. execute_task iterates steps sequentially:
   a. resolve_inputs(step.inputs_template, task.context, prev_output)
      → {{context.key}} resolves from task.context
      → {{prev_output.key}} resolves from previous step's outputs
   b. build ExecutionRequest with resolved inputs
   c. call execute(request) — full engine pipeline
   d. on success: store result in step, update context if output_key set
   e. on failure: mark step FAILED, skip remaining, mark task FAILED

3. Task state persisted in memory store after completion
   → retrievable via GET /tasks/{id}
```

## Data Model

```python
@dataclass
class TaskStep:
    operation: str                    # execution operation name
    inputs_template: dict             # template with {{context.key}} refs
    output_key: str = ""              # store result under this key in context
    execution_class: str = "llm_call" # execution class for engine
    id: str = ""                      # auto-generated step_xxxx
    status: StepStatus                # pending → running → completed/failed/skipped
    result: dict | None = None        # full ExecutionResult.to_dict()

@dataclass
class Task:
    steps: list[TaskStep]
    id: str = ""                      # auto-generated task_xxxx
    status: TaskStatus                # pending → running → completed/failed
    current_step_index: int = 0
    context: dict                     # shared context, enriched per step
    created_at: str = ""
    updated_at: str = ""
    issued_by: str = ""               # identity that created the task
    error: str = ""                   # set on failure
```

## Template Resolution

```
Input:  {"prompt": "Hello {{context.name}}, result was {{prev_output.text}}"}
Context: {"name": "Alice"}
Prev:    {"text": "classified as greeting"}
Output:  {"prompt": "Hello Alice, result was classified as greeting"}
```

- Regex: `\{\{([\w.]+)\}\}`
- Supports nested dict traversal: `{{context.step1.outputs.text}}`
- Nested dict values resolved recursively
- Missing context keys resolve to empty string
- Missing prev_output keys left unchanged (template literal preserved)
- Non-string values passed through without modification

## Safety Mechanisms

1. **Max 10 steps**: Enforced in Task.__post_init__ and API layer
2. **Sequential execution**: No parallel steps — deterministic ordering
3. **Fail-fast**: First step failure stops task, remaining steps SKIPPED
4. **Engine pipeline**: Each step goes through full execute() — guards, events, observers
5. **Identity tracking**: issued_by propagated to all ExecutionRequests
6. **Correlation**: Task ID used as correlation_id for all step executions

## Events Emitted

| Type | When | Payload |
|------|------|---------|
| `task.started` | Task begins | task_id, step_count |
| `task.step.started` | Step begins | task_id, step_id, step_index, operation |
| `task.step.completed` | Step finishes | task_id, step_id, step_index, status |
| `task.completed` | Task finishes | task_id, status, steps_completed or failed_step |

## API Extensions

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| POST | `/tasks` | execute | Create and execute a multi-step task |
| GET | `/tasks/{task_id}` | execute | Retrieve task by ID |

## Memory Store

- In-memory dict keyed by task_id, protected by threading.Lock
- Tasks saved after execution (both success and failure)
- `get_task(id)` / `list_tasks()` / `reset_tasks()` API
- Acceptable for Phase 5E — persistent store deferred

## Backwards Compatibility

- No ExecutionRequest/ExecutionResult schema changes
- No execution engine changes
- No guard, approval, or orchestrator changes
- All Phase 4D/4E/4F/5A/5B/5C/5D tests pass
- API additions only (no endpoint changes)

## Test Results

```
Phase 5E: 43 passed in 355.70s
Cross-phase (4D–5E): 295 passed in 509.39s
```

Test coverage:
- A. Task model (7 tests): creation, step creation, to_dict, max steps, timestamps, context default
- B. Template resolution (9 tests): context ref, prev_output ref, nested, passthrough, non-string, missing keys, nested dict, multiple templates
- C. Single step execution (2 tests): single LLM step, result stored in context
- D. Multi-step execution (5 tests): two-step, context passing, prev_output passing, three-step, initial context
- E. Failure handling (2 tests): failure stops execution, error message set
- F. Task events (5 tests): started, completed, step events, failed events, ordering
- G. Task store (4 tests): saved after execution, failed saved, missing returns None, reset clears
- H. API endpoints (8 tests): auth required, scope required, create+execute, get task, not found, max steps, multi-step via API, initial context via API
- I. Issued by tracking (1 test): task carries issued_by to step executions

## Validation

```bash
python3 -c "from umh.orchestrator.task import Task, TaskStep, execute_task; print('OK')"  # OK
python3 -c "from umh.control.api import app; print('OK')"                                  # OK
```
