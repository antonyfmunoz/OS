# Phase 6E — Bypass & Regression Audit

**Date:** 2026-04-27
**Auditor:** Phase 6E Agent 6 (automated)
**Scope:** umh/control/, umh/planning/, umh/orchestrator/, and cross-cutting checks across umh/

---

## Check 1: Direct adapter calls outside execution backend

```bash
grep -rn "get_adapter\|from umh.execution.adapters" umh/control/ umh/planning/ umh/orchestrator/ 2>/dev/null
```

**Output:** (none)

**Analysis:** CLEAN. No control/planning/orchestrator layer touches adapters directly.

---

## Check 2: subprocess in control/planning/orchestrator layers

```bash
grep -rn "subprocess" umh/control/ umh/planning/ umh/orchestrator/ 2>/dev/null
```

**Output:** (none)

**Analysis:** CLEAN. No subprocess calls in restricted layers.

---

## Check 3: shell=True anywhere in umh

```bash
grep -rn "shell=True" umh/ 2>/dev/null
```

**Output:**
```
umh/adapters/workstation_adapter.py:83:            shell=True,
umh/adapters/execution/workstation_adapter.py:83:            shell=True,
umh/substrate/station_daemon.py:513:  - `subprocess.Popen` is called with a list (never shell=True).
umh/interfaces/telegram/bot.py:258:    """Execute a command from a strict allowlist. No shell=True, no arbitrary input."""
```

**Analysis:**

| File | Verdict | Notes |
|------|---------|-------|
| `adapters/workstation_adapter.py:83` | **MEDIUM** — Real finding | `shell=True` in an adapter's `_run_command()`. The cmd is built from config, but `shell=True` with string input is an injection vector if config is ever user-controlled. Should use list form + `shell=False`. |
| `adapters/execution/workstation_adapter.py:83` | **MEDIUM** — Duplicate of above | Same file exists at two paths (likely a copy during refactor). Same issue. |
| `substrate/station_daemon.py:513` | False positive | Docstring/comment explicitly documenting that `shell=True` is NOT used. |
| `interfaces/telegram/bot.py:258` | False positive | Docstring explicitly documenting that `shell=True` is NOT used. |

---

## Check 4: Direct call_with_fallback bypass (outside model_router)

```bash
grep -rn "call_with_fallback" umh/ 2>/dev/null | grep -v model_router
```

**Output:**
```
umh/stages/llm_generation.py:24
umh/runtime_engine/voice_engine.py:567
umh/runtime_engine/multi_strategy.py:349
umh/adapters/umh_execution.py:519,529
umh/substrate/voice_eos_responder.py:244,252
umh/substrate/meeting_intelligence.py:502,1280
```

**Analysis:** All usages verified to import from `umh.runtime_engine.model_router`:

```
umh/stages/llm_generation.py:22:  from umh.runtime_engine.model_router import call_with_fallback
umh/runtime_engine/multi_strategy.py:331:  from umh.runtime_engine.model_router import call_with_fallback
umh/runtime_engine/voice_engine.py:565:  from umh.runtime_engine.model_router import call_with_fallback
umh/adapters/umh_execution.py:500:  from umh.runtime_engine.model_router import call_with_fallback
umh/substrate/voice_eos_responder.py:229:  from umh.runtime_engine.model_router import call_with_fallback
umh/substrate/meeting_intelligence.py:499,1263:  from umh.runtime_engine.model_router import call_with_fallback
```

**Verdict:** All false positives. Every call goes through model_router. No bypass.

---

## Check 5: Approval store manipulation outside approved modules

```bash
grep -rn "approval_store\|get_approval_store" umh/control/ umh/planning/ umh/orchestrator/ 2>/dev/null
```

**Output:**
```
umh/control/cli.py:177,179
umh/control/api.py:29,166,177,187,211
umh/orchestrator/engine.py:136,151
umh/orchestrator/worker.py:153,158,162
```

**Analysis:**

| Location | Verdict | Notes |
|----------|---------|-------|
| `control/api.py` — approval endpoints | False positive | The control plane API is the **intended** interface for approval management (list/approve/deny). All behind `_require_scope()` auth checks. This is correct architecture. |
| `control/cli.py:177-179` | False positive | CLI `cmd_approvals` — read-only listing of pending approvals. Correct CLI interface behavior. |
| `orchestrator/engine.py:136-151` | False positive | `_build_replay_action` — reads approval status to replay on approval event. Correct orchestrator behavior (checking approval before replaying). |
| `orchestrator/worker.py:153-162` | False positive | `_find_resumable_tasks` — reads approval status to find paused tasks with granted approvals. Correct worker behavior. |

**Verdict:** All false positives. Control plane reads/manages approvals (its job). Orchestrator reads approval status (needed for resume logic). No unauthorized mutation.

---

## Check 6: Direct task mutation in worker/control bypassing store

```bash
grep -rn "_tasks\[" umh/orchestrator/worker.py umh/control/api.py umh/control/cli.py 2>/dev/null
```

**Output:**
```
umh/control/api.py:242:    for t in sorted_tasks[:5]:
```

**Analysis:** False positive. `sorted_tasks[:5]` is a slice of a local variable in `_build_task_metrics()`, not a mutation of `_tasks[]`. The variable name happens to contain `_tasks[` due to the slice syntax, but it's read-only iteration over `list_tasks()` output.

---

## Check 7: Environment bypass (hardcoded environment selection)

```bash
grep -rn "environment.*=.*['\"]real['\"]" umh/ 2>/dev/null
grep -rn "environment.*=.*['\"]sandbox['\"]" umh/ 2>/dev/null
```

**Output:** (none for both)

**Analysis:** CLEAN. No hardcoded environment selection anywhere.

---

## Check 8: Planner executing tasks directly

```bash
grep -rn "execute_task\|execute(" umh/planning/ 2>/dev/null
```

**Output:**
```
umh/planning/planner.py:197:    result = lightweight_execute(
umh/planning/planner.py:284:    Converts plan to task, runs execute_task, updates plan status.
umh/planning/planner.py:292:    from umh.orchestrator.task import execute_task, TaskStatus
umh/planning/planner.py:332:    result = execute_task(task)
```

**Analysis:**

| Location | Verdict | Notes |
|----------|---------|-------|
| `planner.py:197` — `lightweight_execute()` in `_try_llm_plan()` | **LOW** — Acceptable | Uses `lightweight_execute` from `umh.execution.engine` to generate a plan via LLM. This is an LLM call for plan generation, not arbitrary execution. The function name and usage indicate it's a constrained execution path. |
| `planner.py:292-332` — `execute_plan()` | False positive | `execute_plan()` is the **designed** handoff point — it converts a validated plan to a task and routes through `umh.orchestrator.task.execute_task`. This is the correct architecture: planner creates the plan, then delegates execution to the orchestrator's task system. Quality gates (verdict=fail blocks) are enforced before execution. |

---

## Check 9: New imports that could indicate bypass

```bash
grep -rn "from umh.execution.engine import" umh/control/ umh/planning/ 2>/dev/null
```

**Output:**
```
umh/control/api.py:38:from umh.execution.engine import execute
umh/planning/planner.py:179:        from umh.execution.engine import lightweight_execute
```

**Additional check — orchestrator:**
```
umh/orchestrator/task.py:202:    from umh.execution.engine import execute
umh/orchestrator/task.py:379:    from umh.execution.engine import execute
umh/orchestrator/engine.py:141:    from umh.execution.engine import execute
```

**Analysis:**

| Location | Verdict | Notes |
|----------|---------|-------|
| `control/api.py:38` | False positive | Control plane API imports `execute` from the execution engine — this is the correct top-level entry point. The API is the authorized interface for triggering execution, protected by identity/scope checks. |
| `planning/planner.py:179` | **LOW** — Acceptable with note | Uses `lightweight_execute` for LLM plan generation. Goes through the execution engine, not around it. But the planner importing from the execution engine at all is a dependency worth watching — if more execution engine functions leak into the planner, this becomes a coupling concern. |
| `orchestrator/task.py` and `orchestrator/engine.py` | False positive | Orchestrator is the authorized execution coordinator — importing the execution engine is expected and correct. |

---

## Check 10: Guard bypass

```bash
grep -rn "skip_guard\|bypass_guard\|guard.*False" umh/ 2>/dev/null
```

**Output:** (none)

**Analysis:** CLEAN. No guard bypass flags anywhere in the codebase.

---

## Summary

### Real Issues Found

| # | Severity | Location | Issue | Fix |
|---|----------|----------|-------|-----|
| 1 | **MEDIUM** | `umh/adapters/workstation_adapter.py:83` | `shell=True` with string command input. Injection risk if config becomes user-controlled. | Refactor `_run_command()` to accept a list and use `shell=False`. Parse the command string into args with `shlex.split()`. |
| 2 | **MEDIUM** | `umh/adapters/execution/workstation_adapter.py:83` | Duplicate file with same `shell=True` issue. | Same fix as #1. Also: determine which copy is canonical and remove the other. |
| 3 | **LOW** | `umh/planning/planner.py:179` | Planner imports `lightweight_execute` from execution engine for LLM plan generation. Not a bypass today, but creates a coupling vector. | Monitor. If more execution engine functions leak into planner, refactor to pass an execution callback instead of importing directly. |

### False Positives Identified

- **Check 3:** `station_daemon.py` and `telegram/bot.py` — docstrings mentioning `shell=True` to document its absence
- **Check 4:** All `call_with_fallback` usages — every one imports from `umh.runtime_engine.model_router`
- **Check 5:** All approval store access — control plane API (authorized manager), CLI (read-only), orchestrator (read for resume logic)
- **Check 6:** `sorted_tasks[:5]` — local variable slice, not `_tasks[]` dict mutation
- **Check 8:** `execute_plan()` — designed handoff to orchestrator task system with quality gates

### Clean Checks (Zero Findings)

- Check 1: No direct adapter calls in restricted layers
- Check 2: No subprocess in restricted layers
- Check 7: No hardcoded environment selection
- Check 10: No guard bypass flags

---

## Overall Risk Rating: **LOW**

The UMH architecture is clean. The two medium-severity `shell=True` findings are in the adapters layer (which is expected to interact with the OS), not in control/planning/orchestrator. The only real coupling concern is the planner's lightweight import from execution engine, which is architecturally acceptable for now but should be monitored.

No bypass violations found in any restricted layer. No security regressions detected.
