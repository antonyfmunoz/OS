# Phase 6C — UMH MVP Loop Map

**Date:** 2026-04-27
**Scope:** End-to-end execution flow from API entry to result, covering all current code paths.

---

## 1. End-to-End Flow Diagram

```
                          HTTP Request
                               |
                     +---------v----------+
                     |  Control Plane API |
                     |   (umh/control/    |
                     |    api.py)         |
                     +---------+----------+
                               |
            +------------------+------------------+
            |                  |                  |
    POST /execute      POST /plans         POST /tasks
            |                  |                  |
            v                  v                  v
     [Direct Exec]    [Planning Pipeline]  [Task Pipeline]
            |                  |                  |
            |          +-------v--------+         |
            |          | Objective      |         |
            |          | Reconstruction |         |
            |          | (objective.py) |         |
            |          +-------+--------+         |
            |                  |                  |
            |          +-------v--------+         |
            |          | Template Match |         |
            |          | (templates.py) |         |
            |          +---+-------+----+         |
            |              |       |              |
            |          [match]  [no match]        |
            |              |       |              |
            |              |   +---v---------+    |
            |              |   | LLM Planning |   |
            |              |   | (_try_llm)   |   |
            |              |   +---+---------+    |
            |              |       |              |
            |          +---v-------v----+         |
            |          | Validator      |         |
            |          | (validator.py) |         |
            |          +-------+--------+         |
            |                  |                  |
            |          +-------v--------+         |
            |          | Quality Scorer |         |
            |          | (quality.py)   |         |
            |          +-------+--------+         |
            |                  |                  |
            |          +-------v--------+         |
            |          | Explanation    |         |
            |          | (explanation.py)|        |
            |          +-------+--------+         |
            |                  |                  |
            |          POST /plans/{id}/execute   |
            |                  |                  |
            |          +-------v--------+         |
            |          | plan_to_task() |         |
            |          +-------+--------+         |
            |                  |                  |
            |                  +-------+----------+
            |                          |
            |               +----------v-----------+
            |               |  Task Executor       |
            |               |  (orchestrator/      |
            |               |   task.py)           |
            |               +----------+-----------+
            |                          |
            |             for each TaskStep:
            |               +----------v-----------+
            |               | Build ExecutionReq   |
            |               | Resolve templates    |
            +-------------->+----------+-----------+
                                       |
                            +----------v-----------+
                            |  Execution Engine    |
                            |  (execution/         |
                            |   engine.py)         |
                            +----------+-----------+
                                       |
                    +------------------+------------------+
                    |                                     |
             [PURE/LLM_CALL]                     [SIDE_EFFECT]
                    |                                     |
                    |                         +-----------v-----------+
                    |                         |  Security Guard       |
                    |                         |  (security/           |
                    |                         |   execution_guard.py) |
                    |                         +-----------+-----------+
                    |                                     |
                    |                    +----------------+----------------+
                    |                    |                |                |
                    |                [ALLOW]     [REQUIRES_APPROVAL]   [DENY]
                    |                    |                |                |
                    |                    |         +------v------+   return REJECTED
                    |                    |         | Create      |
                    |                    |         | Approval    |
                    |                    |         | Request     |
                    |                    |         +------+------+
                    |                    |                |
                    |                    |         return REJECTED
                    |                    |         (with approval_id)
                    |                    |
                    +--------------------+
                                         |
                              +----------v-----------+
                              |  SpineExecutionBackend|
                              |  (adapters/           |
                              |   umh_execution.py)   |
                              +----------+-----------+
                                         |
                    +--------------------+--------------------+
                    |                    |                    |
              [LLM_CALL]         [shell_command]       [file_*]
                    |                    |                    |
            model_router.        subprocess.run       os.read/
            call_with_            (allowlisted)       scandir/stat
            fallback()
                    |                    |                    |
                    +--------------------+--------------------+
                                         |
                              +----------v-----------+
                              |  ExecutionResult     |
                              +----------+-----------+
                                         |
                              +----------v-----------+
                              |  Observer + Events   |
                              |  (events/stream.py)  |
                              +----------------------+
```

---

## 2. API Endpoint Map

| Method | Path | Scope Required | Purpose | Returns |
|--------|------|----------------|---------|---------|
| GET | `/health` | (none) | Liveness probe | `{"status": "ok"}` |
| POST | `/execute` | `execute` | Direct single-operation execution | ExecutionResult dict |
| POST | `/plans` | `execute` | Create plan from objective or raw input | ExecutionPlan dict (200 if valid, 422 if rejected) |
| GET | `/plans` | `execute` | List all plans | List of plan dicts |
| GET | `/plans/{plan_id}` | `execute` | Get single plan | Plan dict |
| POST | `/plans/{plan_id}/execute` | `execute` | Execute a validated plan as a Task | Task dict or dry_run |
| POST | `/plans/{plan_id}/validate` | `execute` | Re-validate an existing plan | PlanValidationResult dict |
| POST | `/tasks` | `execute` | Create and execute multi-step task directly | Task dict |
| GET | `/tasks` | `execute` | List all tasks | List of task dicts |
| GET | `/tasks/{task_id}` | `execute` | Get single task | Task dict |
| GET | `/approvals` | `approvals:read` | List approvals (optional `?status=pending`) | List of approval dicts |
| GET | `/approvals/{id}` | `approvals:read` | Get single approval | Approval dict |
| POST | `/approvals/{id}/approve` | `approvals:write` | Approve a pending request | `{"approved": id}` |
| POST | `/approvals/{id}/deny` | `approvals:write` | Deny a pending request | `{"denied": id}` |
| GET | `/metrics` | `metrics:read` | Full system metrics (exec + plans + tasks) | Metrics dict |
| POST | `/identities` | `admin` | Create new API identity | Identity dict + raw key |
| GET | `/identities` | `admin` | List all identities | List of identity dicts |
| POST | `/identities/{id}/disable` | `admin` | Disable an identity | `{"disabled": id}` |
| GET | `/orchestrator/rules` | `admin` | List registered orchestrator rules | List of rule dicts |
| GET | `/events` | `metrics:read` | List recent events (limit param) | List of event dicts |
| GET | `/events/stream` | `metrics:read` | SSE event stream (Server-Sent Events) | text/event-stream |

**Total: 20 endpoints** (1 unauthenticated, 19 authenticated)

---

## 3. Data Objects at Each Stage

### Stage 1: API Entry

```
PlanObjectiveBody (Pydantic)
  title: str
  raw_input: str
  description: str
  constraints: list[str]
  context: dict
  max_steps: int (1-10)
  allowed_capabilities: list[str]
  dry_run: bool
```

### Stage 2: Objective Reconstruction (raw_input path)

```
PlanObjective (dataclass)
  title: str                 -- from template_hint or derived
  description: str           -- cleaned raw input
  constraints: list[str]
  context: dict              -- extracted path, text
  requested_by: str
  max_steps: int
  allowed_capabilities: list[str]
  dry_run: bool
  objective_id: str          -- auto-generated
  raw_input: str             -- original text
  intent_category: str       -- system_health, file_inspect, etc.
  inferred_constraints: dict -- dry_run, sandbox flags
  uncertainty: tuple[str]    -- flagged ambiguities
  assumptions: tuple[str]    -- inferred assumptions
```

### Stage 3: Plan Generation

```
ExecutionPlan (dataclass)
  objective: PlanObjective
  steps: list[ExecutionPlanStep]
  source: PlanSource          -- template | llm | manual
  confidence: float           -- 1.0 for template, 0.7 for LLM
  assumptions: list[str]
  status: PlanStatus          -- draft → validated | rejected
  plan_id: str                -- auto-generated
  created_at: str
  task_id: str                -- set after execution
  validation_errors: list[str]
  quality_score: dict | None
  explanation: dict | None

ExecutionPlanStep (dataclass)
  name: str
  operation: str
  inputs: dict
  execution_class: str
  constraints: dict
  depends_on: list[str]
  rationale: str
  step_id: str                -- auto-generated
```

### Stage 4: Validation

```
PlanValidationResult (dataclass)
  valid: bool
  errors: list[str]
  warnings: list[str]
```

### Stage 5: Quality Scoring

```
PlanQualityScore (dataclass)
  score: float (0.0-1.0)
  verdict: str               -- pass (>=0.7) | warn (>=0.4) | fail (<0.4)
  reasons: list[str]
  dimensions: dict[str, float]
    completeness, safety, specificity,
    executability, minimality, constraint_alignment
```

### Stage 6: Plan Explanation

```
PlanExplanation (dataclass)
  objective_summary: str
  steps_summary: list[dict]
  assumptions: list[str]
  risks: list[str]
  approval_requirements: list[str]
  plan_selection_reason: str
  safety_assessment: str
  quality_summary: dict
```

### Stage 7: Task Conversion

```
Task (dataclass)
  steps: list[TaskStep]
  id: str                    -- auto-generated
  status: TaskStatus         -- pending → running → completed|failed|paused
  current_step_index: int
  context: dict              -- accumulates step outputs
  created_at: str
  updated_at: str
  issued_by: str
  error: str
  paused_step_index: int | None
  paused_approval_id: str
  paused_request: dict | None
  paused_reason: str
  pause_count: int
  resumed_at: str

TaskStep (dataclass)
  operation: str
  inputs_template: dict      -- {{context.key}} and {{prev_output.key}} refs
  output_key: str
  execution_class: str
  id: str                    -- auto-generated
  status: StepStatus
  result: dict | None
```

### Stage 8: Execution Request

```
ExecutionRequest (frozen dataclass)
  execution_id: str
  correlation_id: str
  causal_event_id: str
  session_id: str
  operation: str
  inputs: dict
  execution_class: ExecutionClass  -- pure | side_effect | transport | llm_call
  constraints: ExecutionConstraints
    timeout_s, max_retries, sandbox, max_tokens, cost_limit_usd
  target: ExecutionTarget
    node_id, transport
  context: ExecutionContext
    session_id, correlation_id, decision_trace_id, active_goal_id,
    goal_weight, strategy_name, strategy_confidence, memory_snapshot,
    authority_class, agent_type, venture_id, channel, user_id, org_id, metadata
  issued_at: str
  issued_by: str
  idempotency_key: str
  priority: ExecutionPriority
  retry_count: int
```

### Stage 9: Execution Result

```
ExecutionResult (frozen dataclass)
  execution_id: str
  correlation_id: str
  causal_event_id: str
  operation: str
  status: ExecutionStatus     -- succeeded | failed | timed_out | rejected
  outputs: dict
  side_effects: tuple[str]
  error: str | None
  started_at: str
  completed_at: str
  node_id: str
  idempotency_key: str
  execution_hash: str
  retry_count: int
  model_used: str
  tokens_used: dict
  cost_usd: float
  latency_ms: int
```

### Events (throughout)

```
Event (frozen dataclass)
  id: str                    -- evt_{hex}
  type: str                  -- e.g. execution.started, plan.created
  timestamp: str
  payload: dict
  actor_id: str
  execution_id: str
  approval_id: str
```

---

## 4. Three Execution Paths

### Path A: Direct Execute (`POST /execute`)

1. Auth middleware validates X-API-Key
2. Build ExecutionRequest from body (operation, inputs, execution_class)
3. Call `execute(request)` directly
4. Return ExecutionResult

**Use case:** Single atomic operations. No planning, no multi-step.

### Path B: Plan-then-Execute (`POST /plans` + `POST /plans/{id}/execute`)

1. Auth middleware validates X-API-Key
2. If `raw_input` provided: `reconstruct_objective()` infers intent, title, context
3. If `title` provided: build PlanObjective directly
4. `create_plan()` tries template match, falls back to LLM planning
5. `validate_plan()` checks operations, allowlists, dependencies
6. `score_plan()` computes 6-dimension quality score
7. `explain_plan()` generates structured explanation
8. Plan stored in memory, returned to caller
9. Caller reviews, then `POST /plans/{id}/execute`
10. Quality gate: `fail` verdict blocks execution
11. `plan_to_task()` converts plan steps to TaskSteps
12. `execute_task()` runs steps sequentially through execution engine
13. Each step: resolve templates, build ExecutionRequest, call `execute()`
14. If step requires approval: task pauses, returns with approval_id
15. Task result returned

**Use case:** Structured multi-step work with validation and quality gating.

### Path C: Direct Task (`POST /tasks`)

1. Auth middleware validates X-API-Key
2. Validate steps (non-empty, max 10, valid execution_class)
3. Build Task from steps
4. `execute_task()` runs all steps sequentially
5. Same execution pipeline as Path B step 12+

**Use case:** Pre-defined multi-step work without planning layer.

---

## 5. Security and Approval Flow

```
ExecutionRequest arrives at engine
        |
  [is PURE or LLM_CALL?] ──yes──> bypass guard, execute directly
        |
       no (SIDE_EFFECT / TRANSPORT)
        |
  [has approval_id?] ──yes──> validate_for_execution()
        |                          |
       no                    [valid?] ──yes──> execute with approved flag
        |                          |
        |                    [invalid] ──> return REJECTED
        |
  check_execution() in security guard
        |
  [shell_command] ──> check metachar deny + allowlist in backend
  [file_*]        ──> check sandbox roots + denied patterns
  [computer_*]    ──> safe ops ALLOW; mutation ops REQUIRES_APPROVAL
  [browser_*]     ──> DENY (not implemented)
  [os_*]          ──> DENY (not implemented)
  [unknown]       ──> DENY
        |
  [REQUIRES_APPROVAL]
        |
  Create ApprovalRequest (300s TTL)
  Store pending request in orchestrator
  Return REJECTED + approval_id
        |
  User approves via POST /approvals/{id}/approve
        |
  Event "approval.approved" published
        |
  Orchestrator rules fire:
    1. resume_paused_task (if task is paused)
    2. replay_on_approval (if standalone execution)
```

### Approval States

```
PENDING ──approve──> APPROVED ──consume──> CONSUMED
   |                    |
   expire               expire
   |                    |
   v                    v
EXPIRED              EXPIRED
   |
  deny
   |
   v
DENIED
```

---

## 6. Capability Status Map

| Capability | Operations | Status | Guard | Backend |
|-----------|-----------|--------|-------|---------|
| LLM Call | classify_intent, extract_entities, summarize, short_response, validation, + 7 more | ACTIVE | bypass (PURE/LLM_CALL) | model_router.call_with_fallback |
| Shell Command | 12 allowlisted commands | ACTIVE | allowlist + metachar deny | subprocess.run |
| File Read | file_read | ACTIVE | sandbox (/opt/OS/data, /opt/OS/logs, /opt/OS/10_Wiki, /tmp) | os.open |
| File List | file_list | ACTIVE | sandbox | os.scandir |
| File Stat | file_stat | ACTIVE | sandbox | os.stat |
| File Write | file_write | STUB | sandbox (guard allows, backend rejects) | not implemented |
| File Delete | file_delete | STUB | sandbox (guard allows, backend rejects) | not implemented |
| Computer Read | screenshot, screen_size, active_window | ACTIVE | read-only ALLOW | PIL/xdpyinfo |
| Computer Mutation | click, type, key, scroll, drag | ACTIVE (approval-gated) | REQUIRES_APPROVAL | xdotool |
| Browser | navigate, click, type, etc. | STUB | DENY | not implemented |
| OS Interaction | * | NOT_WIRED | DENY | not implemented |

---

## 7. Template Registry (Built-in Plans)

| Template Name | Steps | Operations Used |
|--------------|-------|-----------------|
| `inspect_system_status` | 4 | shell_command x4 (uptime, df -h, free -h, docker ps) |
| `inspect_file` | 1 | file_read |
| `list_directory` | 1 | file_list |
| `summarize_text` | 1 | summarize (LLM) |
| `shell_health_check` | 3 | shell_command x3 (loadavg, df, free) |
| `computer_screenshot_review` | 2 | computer_screenshot + summarize (LLM) |

---

## 8. Event Types Emitted

| Event Type | Emitter | When |
|-----------|---------|------|
| `objective.reconstructed` | planner.py | Raw input parsed into objective |
| `plan.created` | planner.py | Plan generated and validated |
| `plan.validated` | planner.py | Validation passed |
| `plan.rejected` | planner.py | Validation failed or no template |
| `plan.quality_scored` | planner.py | Quality score computed |
| `plan.executed` | planner.py | Plan converted to task and started |
| `plan.execution_blocked_quality` | planner.py | Quality fail blocked execution |
| `execution.started` | execution/engine.py | Every execute() call |
| `execution.completed` | execution/engine.py | Every execute() return |
| `task.started` | orchestrator/task.py | Task begins |
| `task.step.started` | orchestrator/task.py | Step begins |
| `task.step.completed` | orchestrator/task.py | Step ends |
| `task.paused` | orchestrator/task.py | Step needs approval |
| `task.resumed` | orchestrator/task.py | Paused task resumes |
| `task.completed` | orchestrator/task.py | Task finishes (success or fail) |
| `approval.created` | approval.py | Approval request generated |
| `approval.approved` | approval.py | Approval granted |
| `approval.denied` | approval.py | Approval denied |
| `approval.consumed` | approval.py | Approval used for execution |
| `orchestration.triggered` | orchestrator/engine.py | Rule matched |
| `orchestration.executed` | orchestrator/engine.py | Replay executed |

---

## 9. Storage Layer

| Store | Backend | Persistence | Location |
|-------|---------|-------------|----------|
| Plans | In-memory dict + lock | Process lifetime only | `planner._plans` |
| Tasks | In-memory dict + lock | Process lifetime only | `task._tasks` |
| Approvals | SQLite (prod) / in-memory (test) | Disk-durable | `/opt/OS/data/runtime/approvals.sqlite` |
| Identities | SQLite (prod) / in-memory (test) | Disk-durable | `/opt/OS/data/runtime/identities.sqlite` |
| Events | In-memory deque (10K cap) | Process lifetime only | `stream._events` |
| Orchestrator rules | In-memory | Process lifetime only | `engine._rules` |
| Scoring stats | In-memory | Process lifetime only | capability_scorer |
| Metrics | Computed on-demand | N/A | aggregated from above |

---

## 10. Bypasses and Ambiguities Found

### B1: Shell allowlist mismatch between guard and backend

The security guard (`execution_guard.py`) does NOT maintain a shell allowlist -- it only checks for metacharacter injection. The actual allowlist enforcement is in `SpineExecutionBackend._SHELL_ALLOWLIST` (umh_execution.py). Meanwhile, the plan validator (`validator.py`) has its own `_SHELL_ALLOWLIST` with a different set of commands.

**Three different allowlists:**
- `validator.py`: uptime, df -h, free -h, ps aux, whoami, hostname, uname -a, date, ls, ls -la, cat /proc/loadavg, docker ps (12 commands)
- `umh_execution.py`: git status, git log --oneline -10, git diff --stat, docker ps, docker ps -a, uptime, df -h, free -h, date, whoami, python3 --version, pip list (12 commands)
- Only 5 commands overlap: uptime, df -h, free -h, docker ps, date, whoami

**Impact:** A plan validated with `ps aux` will pass validation but fail execution. `ls` passes validation but will be rejected by the backend.

### B2: PURE and LLM_CALL bypass security guard entirely

The execution engine skips the security guard for PURE and LLM_CALL classes. This is intentional but means any operation can be run without guard checks by setting `execution_class: "llm_call"` in the direct `/execute` endpoint.

### B3: Plan and Task stores are in-memory only

Plans and tasks are lost on process restart. Events are also in-memory. Only approvals and identities survive restarts.

### B4: Orchestrator not auto-started

`start_orchestrator()` must be called explicitly. If the API starts without it, the built-in rules (resume task on approval, replay on approval) never fire. The approval flow completes but nothing automatically re-executes.

### B5: file_write/file_delete guard allows but backend rejects

The security guard's `check_file_operation()` returns ALLOW for write/delete operations within sandbox paths, but `SpineExecutionBackend._execute_side_effect()` returns NOT_IMPLEMENTED. The guard gives a false sense of capability.

### B6: Dual shell allowlist check path

For shell_command execution, the guard checks metacharacters, then the backend checks its own allowlist independently. A command can pass the guard but fail the backend (any non-metachar command not in the backend's allowlist). This is defense-in-depth but the two layers don't share a single source of truth.

### B7: LLM planning depends on lightweight_execute

`_try_llm_plan()` imports `lightweight_execute` from the execution engine, creating a circular dependency path: planning imports execution to generate plans that will be validated and then executed. If the LLM backend is unavailable, this silently falls through to "no template found" rejection.

### B8: No plan re-execution path

Once a plan reaches COMPLETED or FAILED status, there's no endpoint to re-execute it. The user must create a new plan from scratch.

### B9: Template matching is exact title match only

`get_template(objective.title)` does exact string lookup. If the objective reconstruction sets `title = "inspect_system_status"`, the template matches. But any variation (e.g., "Inspect System Status" or "system_status_inspect") will miss the template.

### B10: No task resume endpoint

When a task pauses for approval, the orchestrator handles resume automatically via events. But there is no `POST /tasks/{id}/resume` endpoint for manual resume. If the orchestrator is not started, paused tasks are stuck.

---

## 11. Missing Usability Pieces

### Critical (blocks real use)

1. **No CLI tool** -- No command-line interface for creating identities, submitting plans, checking status. Only raw HTTP with curl.
2. **No bootstrapping script** -- No way to create the first admin identity without writing Python directly.
3. **Orchestrator auto-start** -- The API does not call `start_orchestrator()` at startup. Approval-driven resume is dead without it.
4. **Shell allowlist alignment** -- The three independent allowlists must converge to a single source of truth.
5. **Plan/Task persistence** -- In-memory stores mean all state is lost on restart.

### Important (degrades experience)

6. **No task resume endpoint** -- Manual intervention path for paused tasks.
7. **No plan re-execute** -- Ability to re-run a completed/failed plan.
8. **No error detail in plan rejection response** -- The 422 response contains the plan dict but doesn't surface validation errors prominently.
9. **No `DELETE` endpoints** -- Cannot clean up old plans, tasks, identities.
10. **No pagination** -- List endpoints return everything. Will break at scale.

### Nice-to-have (polish)

11. **Swagger/OpenAPI docs** -- `docs_url=None` and `redoc_url=None` are set. No API docs served.
12. **Rate limiting** -- No request rate limits on any endpoint.
13. **Request logging middleware** -- No structured request/response logging beyond events.
14. **Webhook notifications** -- No way to get notified of approval requests except polling.
15. **Template discovery endpoint** -- No `GET /templates` to see available plan templates.

---

## 12. Recommended MVP Completion Checklist

### Phase 6C-1: Critical wiring (make it actually work end-to-end)

- [ ] Add `start_orchestrator()` call to API startup (in `app` lifespan or startup event)
- [ ] Unify shell allowlists into a single module imported by validator, guard, and backend
- [ ] Add `POST /tasks/{task_id}/resume` endpoint for manual task resume
- [ ] Add `GET /templates` endpoint to discover available plan templates
- [ ] Create bootstrap script: `python3 -m umh.control.bootstrap` to create first admin identity

### Phase 6C-2: Persistence (survive restarts)

- [ ] SQLite persistence for plans (already exists for approvals/identities -- follow same pattern)
- [ ] SQLite persistence for tasks
- [ ] Event persistence (SQLite or append-only file)

### Phase 6C-3: CLI (make it usable without curl)

- [ ] `umh identity create <name> --scopes admin` -- create identity
- [ ] `umh plan "check system health"` -- create plan from raw input
- [ ] `umh plan execute <plan_id>` -- execute validated plan
- [ ] `umh task list` -- list tasks
- [ ] `umh approve <approval_id>` -- approve pending request
- [ ] `umh status` -- show system status (metrics summary)
- [ ] `umh events --follow` -- tail event stream

### Phase 6C-4: Hardening

- [ ] Enable Swagger docs (`docs_url="/docs"`)
- [ ] Add pagination to list endpoints (offset/limit)
- [ ] Add `DELETE /plans/{id}` and `DELETE /tasks/{id}`
- [ ] Add plan re-execute (`POST /plans/{id}/re-execute` that clones and runs)
- [ ] Webhook/callback for approval notifications

---

## 13. Architecture Summary

The system is architecturally sound. The separation between planning, orchestration, execution, and events is clean. The approval flow with orchestrator-driven resume is well-designed. The security guard provides real defense-in-depth.

The primary gap is operational: the system cannot be bootstrapped, operated, or monitored without writing raw Python or curl commands. The three shell allowlists are the most dangerous correctness issue -- a plan that validates successfully can fail at execution, which breaks the user's trust in the planning layer.

The in-memory stores for plans and tasks are the biggest durability risk. Everything else (approvals, identities) already uses SQLite -- extending the pattern is straightforward.

**Files read for this audit:**
- `/opt/OS/umh/control/api.py` -- 623 lines
- `/opt/OS/umh/control/identity.py` -- 274 lines
- `/opt/OS/umh/planning/models.py` -- 159 lines
- `/opt/OS/umh/planning/planner.py` -- 367 lines
- `/opt/OS/umh/planning/validator.py` -- 160 lines
- `/opt/OS/umh/planning/templates.py` -- 205 lines
- `/opt/OS/umh/planning/quality.py` -- 277 lines
- `/opt/OS/umh/planning/explanation.py` -- 168 lines
- `/opt/OS/umh/planning/objective.py` -- 171 lines
- `/opt/OS/umh/planning/directive_engine.py` -- 494 lines
- `/opt/OS/umh/planning/plan_mutation.py` -- (scanned)
- `/opt/OS/umh/orchestrator/task.py` -- 607 lines
- `/opt/OS/umh/orchestrator/engine.py` -- 311 lines
- `/opt/OS/umh/execution/engine.py` -- 407 lines
- `/opt/OS/umh/execution/contract.py` -- 352 lines
- `/opt/OS/umh/execution/approval.py` -- 314 lines
- `/opt/OS/umh/execution/interfaces.py` -- 142 lines
- `/opt/OS/umh/execution/metrics.py` -- 210 lines
- `/opt/OS/umh/execution/environment.py` -- 299 lines
- `/opt/OS/umh/execution/external.py` -- 90 lines
- `/opt/OS/umh/events/stream.py` -- 150 lines
- `/opt/OS/umh/security/execution_guard.py` -- 226 lines
- `/opt/OS/umh/adapters/base.py` -- 189 lines
- `/opt/OS/umh/adapters/bridge.py` -- 50 lines
- `/opt/OS/umh/adapters/umh_execution.py` -- 679 lines
- `/opt/OS/umh/adapters/computer_use_adapter.py` -- 493 lines
