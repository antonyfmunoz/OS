# Phase 6A: Deterministic Planning Layer v1 — Completion Report

**Date:** 2026-04-27
**Status:** Complete

---

## Files Created

| File | Purpose |
|------|---------|
| `umh/planning/models.py` | PlanObjective, ExecutionPlan, ExecutionPlanStep, PlanValidationResult, PlanStatus, PlanSource |
| `umh/planning/validator.py` | validate_plan() — operation allowlist, shell allowlist, execution class, dependency, capability checks |
| `umh/planning/templates.py` | Decorator-based template registry, 6 deterministic templates |
| `umh/planning/planner.py` | create_plan(), plan_to_task(), execute_plan(), LLM fallback, in-memory plan store |
| `tests/unit/test_phase6a.py` | 64 tests across 9 categories |

## Files Modified

| File | Change |
|------|---------|
| `umh/control/api.py` | Added 5 plan endpoints (POST/GET /plans, GET/POST /plans/{id}/*, POST /plans/{id}/validate), plan metrics |

---

## Architecture

```
PlanObjective
    │
    ▼
create_plan()
    │
    ├─ _try_template()  ←── template registry (6 templates)
    │                        confidence=1.0, deterministic
    │
    ├─ _try_llm_plan()  ←── lightweight_execute() + JSON parse
    │                        confidence=0.7, untrusted
    │
    └─ (no match)       ←── REJECTED, "no_template"
    │
    ▼
validate_plan()
    │
    ├─ Errors → REJECTED
    │
    └─ Valid → VALIDATED
         │
         ▼
    plan_to_task()  →  Task with TaskSteps
         │
         ▼
    execute_task()  →  existing execution substrate
```

## Templates

| Template | Steps | Operations |
|----------|-------|------------|
| `inspect_system_status` | 4 | shell_command (uptime, df, free, docker ps) |
| `inspect_file` | 1 | file_read |
| `list_directory` | 1 | file_list |
| `summarize_text` | 1 | summarize (llm_call) |
| `shell_health_check` | 3 | shell_command (loadavg, df, free) |
| `computer_screenshot_review` | 2 | computer_screenshot + summarize |

## Validator Rules

1. Empty plan → error
2. Step count > min(objective.max_steps, 10) → error
3. Duplicate step_id → error
4. Unknown operation → error
5. Unsupported operation (browser_*, os_*) → error
6. Invalid execution_class → error
7. Non-dict inputs → error
8. Shell command not in allowlist → error
9. Operation not in allowed_capabilities → error
10. depends_on references unknown/later step → error
11. Approval-gated op without side_effect class → error
12. Approval-gated op → warning

## Security Boundaries

- **Shell allowlist:** 12 commands (uptime, df -h, free -h, ps aux, whoami, hostname, uname -a, date, ls, ls -la, cat /proc/loadavg, docker ps)
- **Unsupported ops:** browser_navigate, browser_click, browser_type, os_reboot, os_shutdown, os_install
- **Approval-gated ops:** computer_click, computer_type, computer_key, computer_scroll, computer_drag
- **LLM plans:** Treated as untrusted, must pass same validator as template plans

## Events Emitted

| Event | When |
|-------|------|
| `plan.created` | Plan passes validation |
| `plan.validated` | Plan passes validation (with warnings) |
| `plan.rejected` | Plan fails validation or no template |
| `plan.executed` | Plan converted to task and dispatched |

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/plans` | Create plan from objective |
| GET | `/plans` | List all plans |
| GET | `/plans/{plan_id}` | Get single plan |
| POST | `/plans/{plan_id}/execute` | Execute validated plan |
| POST | `/plans/{plan_id}/validate` | Re-validate existing plan |

## Test Results

**64 tests, 64 passed, 0 failures (282s)**

| Category | Count | Coverage |
|----------|-------|----------|
| A. Models | 9 | Dataclass creation, defaults, enums, objective fields |
| B. Templates | 8 | Registry, all 6 templates, max_steps capping |
| C. Validator | 13 | All 12 rules, multi-error accumulation |
| D. Task conversion | 5 | Validated→Task, rejected plan refusal, step mapping |
| E. Execution integration | 9 | create_plan template path, LLM fallback, dry run, plan store |
| F. API | 11 | All 5 endpoints, error cases, plan lifecycle |
| G. Metrics | 2 | Plan metrics structure and counts |
| H. Events | 4 | Created, validated, rejected, executed events |
| I. Regression | 3 | Phase 5 imports, existing task system, approval flow |

## Regression Impact

- Phase 5 full suite: **363 passed, 0 failures**
- No existing tests modified
- No schema changes
- No changes to execution substrate

## Invariant Compliance

| # | Invariant | Status |
|---|-----------|--------|
| 1 | No autonomous agent behavior | Plans are deterministic templates or validated LLM output |
| 2 | Template-first, LLM optional | _try_template() before _try_llm_plan() |
| 3 | LLM output is untrusted | Same validate_plan() applied to all sources |
| 4 | Plans convert to existing Tasks | plan_to_task() produces Task with TaskSteps |
| 5 | No new execution paths | execute_plan() calls execute_task() |
| 6 | No schema changes | In-memory plan store only |
| 7 | No new dependencies | Uses only existing umh modules |
| 8 | Validator is deterministic | Pure function, no I/O, no randomness |
| 9 | Step count hard-capped at 10 | _MAX_STEPS = 10, enforced in validator |
| 10 | Shell commands allowlisted | _SHELL_ALLOWLIST checked for every shell_command step |
