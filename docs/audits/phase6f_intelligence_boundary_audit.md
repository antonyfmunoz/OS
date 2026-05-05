# Phase 6F — Intelligence Boundary Audit

**Date:** 2026-04-27
**Auditor:** Phase 6F Agent 6
**Scope:** Verify that the intelligent execution bridge (raw input -> objective -> plan -> task -> execution) maintains correct layer separation. Execution must only occur in the execution layer.

---

## 1. Objective Reconstruction Does Not Execute

**Command:**
```bash
grep -rn "execute\|subprocess\|adapter" umh/planning/objective.py
```

**Output:**
```
umh/planning/objective.py:133: assumptions.append("Computer use adapter is available")
```

**Analysis:** FALSE POSITIVE. Line 133 is a string literal in an assumptions list — it describes that a computer use adapter would be needed, it does not import or call one. The word "adapter" appears only inside a string constant. No execution occurs.

**Verdict:** CLEAN

---

## 2. Planning Does Not Execute (Direct)

**Command:**
```bash
grep -rn "from umh.execution.engine\|execute(" umh/planning/planner.py
```

**Output:**
```
umh/planning/planner.py:179: from umh.execution.engine import lightweight_execute
umh/planning/planner.py:197: result = lightweight_execute(
```

**Analysis:** VIOLATION (MEDIUM severity). The `_try_llm_plan()` function at line 176 imports and calls `lightweight_execute()` from the execution engine. This is an LLM call to generate a plan when no template matches. The `lightweight_execute()` function routes through the full execution engine pipeline (guard -> adapter -> result).

This means the planning layer triggers execution to generate the plan itself. While this is an LLM-only call (not a side-effecting mutation), it breaks the "planning is pure" contract. The planning layer should not reach into execution.engine for any purpose.

**Mitigating factors:**
- `lightweight_execute()` with `operation="plan_generation"` is an LLM inference call, not a mutation
- The execution guard still runs, so security is not bypassed
- The result is only used to parse plan structure, not to execute the plan

**Recommendation:** Extract the LLM dispatch into a separate `umh/planning/llm_assist.py` that calls the model router directly (not through the execution engine). This keeps the planning layer pure while still allowing LLM-assisted plan generation.

**Verdict:** BOUNDARY VIOLATION — medium severity

---

## 3. Quality Does Not Execute

**Command:**
```bash
grep -rn "execute\|subprocess\|adapter" umh/planning/quality.py
```

**Output:**
```
umh/planning/quality.py:201: """Can this plan actually execute successfully?"""
```

**Analysis:** FALSE POSITIVE. Line 201 is a docstring for the `_score_executability()` function. The word "execute" appears only in documentation. No execution imports or calls.

**Verdict:** CLEAN

---

## 4. Explanation Does Not Execute

**Command:**
```bash
grep -rn "execute\|subprocess\|adapter" umh/planning/explanation.py
```

**Output:** (empty — exit code 1, no matches)

**Analysis:** No hits. Explanation layer is completely pure.

**Verdict:** CLEAN

---

## 5. API/CLI Only Enqueue Through Task System

**Command:**
```bash
grep -rn "from umh.execution.engine import\|execute(" umh/control/api.py umh/control/cli.py
```

**Output:**
```
umh/control/api.py:38:  from umh.execution.engine import execute
umh/control/api.py:224: result = execute(exec_request)
umh/control/cli.py:92:  def cmd_execute(args: argparse.Namespace) -> int:
```

**Analysis:** MIXED.

- **api.py (VIOLATION — LOW severity):** The `/execute` endpoint at line 202-225 imports `execute()` directly from `umh.execution.engine` and calls it without going through the task system. This creates a bypass path: API callers can hit execution directly without plan validation, quality scoring, or task tracking. However, the execution guard still runs (line 159 of engine.py), so security is maintained.

- **cli.py (CLEAN):** The `cmd_execute` function name is a false positive. The actual implementation at line 317-362 routes through `create_plan_from_raw()` -> `execute_plan()` -> task system. Both `cmd_execute` and `cmd_run` properly use the `execute_plan()` bridge function from planner.py.

**Recommendation:** The API `/execute` endpoint should be either:
1. Documented as a low-level escape hatch (power-user only, requires explicit scope), or
2. Refactored to route through the task system like the CLI does

**Verdict:** api.py has a direct-execution bypass (LOW severity, guard still applies). cli.py is CLEAN.

---

## 6. Task System Executes Only Through execute()

**Command:**
```bash
grep -rn "from umh.execution.engine import\|execute(" umh/orchestrator/task.py
```

**Output:**
```
umh/orchestrator/task.py:202: from umh.execution.engine import execute
umh/orchestrator/task.py:259: result = execute(request)
umh/orchestrator/task.py:379: from umh.execution.engine import execute
umh/orchestrator/task.py:445: result = execute(resumed_request)
umh/orchestrator/task.py:531: next_result = execute(next_request)
```

**Analysis:** CORRECT BEHAVIOR. The task system (`execute_task`, `resume_task`) is the designated bridge layer. It:
1. Builds `ExecutionRequest` objects with full metadata (task_id, step_id, step_index)
2. Routes each step through `execute()` from the execution engine
3. Handles approval pausing (lines 265-269, 449-454, 537-539)
4. Continues sequential execution after approval

All three `execute()` calls (initial step, resumed step, continuation steps) follow the same pattern: construct request -> call execute() -> check result -> handle approval/failure.

**Verdict:** CORRECT — this is exactly where execution should occur

---

## 7. Approvals Still Gate Mutations

**Command:**
```bash
grep -rn "requires_approval\|approval_id\|guard" umh/execution/engine.py
```

**Output:** 29 matches spanning lines 99-292, including:
- `approval_id` extraction from request inputs (line 101)
- Pre-guard approval check (lines 102-138)
- Security guard for non-LLM execution (lines 159-237)
- `GuardVerdict.REQUIRES_APPROVAL` handling (line 166)
- Approval creation and return (lines 186-201, 216-217)
- Guard denial path (lines 224-237)
- Approval consumption on success (lines 289-292)

**Analysis:** CORRECT BEHAVIOR. The approval system is comprehensive:
1. Pre-guard: checks if an `approval_id` was already provided (resumed task)
2. Guard check: `check_execution()` returns `REQUIRES_APPROVAL`, `ALLOW`, or `DENY`
3. On `REQUIRES_APPROVAL`: creates approval record, returns result with `requires_approval=True`
4. On `DENY`: blocks execution with guard denial error
5. On success with approval: consumes the approval token (line 292)

The guard applies to all non-LLM execution classes, and there is no code path that bypasses it.

**Verdict:** CORRECT — approvals properly gate mutations

---

## 8. No New LLM Calls Outside Sanctioned Paths

**Command:**
```bash
grep -rn "call_with_fallback\|anthropic\|openai\|genai\|ollama" umh/control/ umh/planning/ umh/orchestrator/
```

**Output:** (empty — exit code 1, no matches)

**Analysis:** No direct LLM SDK imports or calls exist in control, planning, or orchestrator layers. All LLM interaction is routed through the execution engine.

Note: This finding strengthens the violation in Check 2 — the planning layer's only way to make LLM calls is by importing `lightweight_execute` from the execution engine, which is the wrong abstraction boundary but at least ensures all LLM calls go through the engine pipeline.

**Verdict:** CLEAN

---

## 9. No Direct Tool/Adapter Calls in Control/Planning/Orchestrator

**Command:**
```bash
grep -rn "get_adapter\|from umh.adapters\|from umh.execution.adapters" umh/control/ umh/planning/ umh/orchestrator/
```

**Output:** (empty — exit code 1, no matches)

**Analysis:** No adapter imports or calls exist outside the execution layer. Tool/adapter dispatch is completely contained within the execution engine.

**Verdict:** CLEAN

---

## 10. No Recursive Agent Loops

**Command:**
```bash
grep -rn "while.*True\|recursive\|self_call\|agent_loop" umh/control/ umh/planning/ umh/orchestrator/
```

**Output:**
```
umh/control/api.py:822:       while True:
umh/orchestrator/worker.py:215: while True:
```

**Analysis:** FALSE POSITIVES (both).

- **api.py:822** — SSE event generator loop. `while True` polls a queue for events and yields them as Server-Sent Events. It sleeps 0.1s between polls and has a `finally` block that cleans up the subscription. This is a standard async generator pattern, not a recursive agent loop.

- **worker.py:215** — Main worker keepalive loop. `while True: time.sleep(1)` keeps the worker process alive until `KeyboardInterrupt`. Standard daemon pattern.

Neither is a recursive agent loop, self-calling function, or unbounded autonomous agent.

**Verdict:** CLEAN

---

## Data Flow Diagram

```
User input (string)
  |
  v
reconstruct_objective()                    [umh/planning/objective.py]
  STATUS: PURE FUNCTION
  - Pattern matching, string parsing
  - No imports from execution layer
  - Only string "adapter" in an assumptions list (benign)
  |
  v
create_plan()                              [umh/planning/planner.py]
  STATUS: MOSTLY PURE (one violation)
  - Template matching: PURE
  - _try_llm_plan(): IMPURE — calls lightweight_execute()
    from umh.execution.engine (MEDIUM violation)
  |
  v
validate_plan()                            [umh/planning/validator.py]
  STATUS: PURE
  - Structure validation only
  |
  v
score_plan()                               [umh/planning/quality.py]
  STATUS: PURE
  - Scoring logic only, no execution imports
  |
  v
explain_plan()                             [umh/planning/explanation.py]
  STATUS: PURE
  - Text generation only, zero execution imports
  |
  v
execute_plan()                             [umh/planning/planner.py]
  STATUS: BRIDGE (correct role)
  - Converts plan to Task via plan_to_task()
  - Calls execute_task() from orchestrator
  - Quality gate blocks verdict=fail plans
  - Dry run gate prevents execution when flagged
  |
  v
execute_task() / resume_task()             [umh/orchestrator/task.py]
  STATUS: BRIDGE (correct role)
  - Iterates steps sequentially
  - Builds ExecutionRequest per step
  - Calls execute() from engine
  - Handles approval pausing/resuming
  |
  v
execute()                                  [umh/execution/engine.py]
  STATUS: EXECUTION (correct role)
  - Pre-guard: checks existing approval_id
  - Security guard: check_execution() -> ALLOW/DENY/REQUIRES_APPROVAL
  - Adapter dispatch: routes to correct backend
  - Post-guard: consumes approval on success
```

**Bypass path (documented):**
```
API /execute endpoint                      [umh/control/api.py:202]
  |
  v  (skips plan/task layers)
execute()                                  [umh/execution/engine.py]
  - Guard still applies
  - No plan validation or quality scoring
```

---

## Violations Summary

| # | Location | Severity | Description |
|---|----------|----------|-------------|
| 1 | `umh/planning/planner.py:179` | MEDIUM | Planning layer imports and calls `lightweight_execute()` from execution engine to generate LLM-assisted plans. Breaks "planning is pure" contract. |
| 2 | `umh/control/api.py:38,224` | LOW | `/execute` endpoint calls `execute()` directly, bypassing plan validation, quality scoring, and task tracking. Guard still applies. |

---

## False Positives

| # | Location | Why False Positive |
|---|----------|--------------------|
| 1 | `objective.py:133` | String literal "Computer use adapter is available" in assumptions list |
| 2 | `quality.py:201` | Docstring "Can this plan actually execute successfully?" |
| 3 | `cli.py:92` | Function name `cmd_execute` — implementation routes through task system correctly |
| 4 | `api.py:822` | SSE event generator `while True` loop — standard async pattern |
| 5 | `worker.py:215` | Daemon keepalive `while True` loop — standard pattern |

---

## Overall Risk Rating

**LOW-MEDIUM**

The system is well-structured overall. The two violations are:

1. **The planning-layer LLM call (MEDIUM)** is architecturally wrong but operationally safe — it goes through the full engine pipeline including guards, so it cannot cause unauthorized mutations. The fix is straightforward (extract to a dedicated LLM assist module).

2. **The API direct-execute bypass (LOW)** is likely intentional as a power-user/admin endpoint. It still goes through the security guard, so mutations require approval. The risk is that API callers skip plan validation and quality scoring, which could allow poorly structured requests. The fix is either documentation or routing through the task system.

No critical violations. No unbounded loops. No adapter leaks. No unsanctioned LLM calls. Approval gates are comprehensive and correctly implemented.

---

## Recommendations

1. **Extract LLM assist from planner** — Move `_try_llm_plan()` to use a dedicated `umh/planning/llm_assist.py` module that calls the model router directly, not through `lightweight_execute()`. This restores planning-layer purity.

2. **Document or restrict `/execute` endpoint** — Either:
   - Add explicit documentation that `/execute` is a low-level admin endpoint that bypasses plan/quality validation, or
   - Refactor to route through the task system (preferred for consistency)

3. **No other action needed** — All other boundaries are correctly maintained. The task system, approval system, guard system, and adapter isolation are all working as designed.
