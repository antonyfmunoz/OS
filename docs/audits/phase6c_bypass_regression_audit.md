# Phase 6c: Bypass Regression Audit

**Date:** 2026-04-27
**Auditor:** Developer Agent (Claude Opus 4.6)
**Scope:** umh/planning/, umh/control/, umh/orchestrator/, umh/execution/, umh/security/, umh/adapters/, umh/events/
**Method:** Targeted grep across all audit-scoped directories, manual file review of flagged hits

---

## Grep Commands Used

```bash
# 1. subprocess in planning/control/orchestrator
grep -rn 'subprocess\.\(run\|Popen\|call\)' umh/planning/ umh/control/ umh/orchestrator/

# 2. call_with_fallback across all UMH
grep -rn 'call_with_fallback' umh/ --include="*.py"

# 3. Direct adapter imports outside execution layer
grep -rn 'from umh\.adapters\.' umh/ --include="*.py" | grep -v '/umh/execution/' | grep -v '/umh/adapters/'

# 4. shell=True anywhere in UMH
grep -rn 'shell=True' umh/ --include="*.py"

# 5. Dangerous system calls
grep -rn 'os\.system(' umh/ --include="*.py"

# 6. Hardcoded API keys/secrets (pattern match)
grep -rn -E '(api_key|apikey|secret_key|password)\s*=\s*["'\''][A-Za-z0-9_\-]{20,}' umh/ --include="*.py"
grep -rn -E '(sk-[a-zA-Z0-9]{20,}|AIza[a-zA-Z0-9]{30,}|ghp_[a-zA-Z0-9]{20,})' umh/ --include="*.py"

# 7. Approval bypass patterns
grep -rn -i 'skip_approval\|bypass_approval\|no_approval\|approval.*False\|approved.*=.*True' umh/ --include="*.py"

# 8. Sandbox/environment bypass patterns
grep -rn -i 'skip_sandbox\|bypass_sandbox\|no_sandbox\|sandbox.*False\|skip_environment\|bypass_environment' umh/ --include="*.py"

# 9. validate_plan usage
grep -rn 'validate_plan\|plan_validator\|PlanValidator' umh/ --include="*.py"

# 10. Direct execute() calls in planning/control/orchestrator
grep -rn '\.execute(' umh/planning/ umh/control/ umh/orchestrator/ --include="*.py"

# 11. subprocess in adapters layer
grep -rn 'import subprocess\|subprocess\.\(run\|Popen\|call\)' umh/adapters/ --include="*.py"

# 12-14. subprocess in execution/security/events
grep -rn 'import subprocess\|subprocess\.\(run\|Popen\|call\)' umh/execution/ umh/security/ umh/events/ --include="*.py"

# 15. Direct LLM SDK imports in planning layer
grep -rn 'import anthropic\|import openai\|from anthropic\|from openai\|from google\.genai' umh/planning/ --include="*.py"

# 16. Plan execution paths
grep -rn 'execute_plan\|run_plan\|_execute_plan' umh/ --include="*.py"

# 17. force=True bypass
grep -rn 'force=True\|force=' umh/planning/planner.py umh/control/api.py

# 18. shell=True in os_controller.py
grep -n 'shell=True' umh/substrate/os_controller.py

# 19. dispatch_enforcement.py subprocess
grep -n -B5 -A10 'subprocess.run' umh/substrate/dispatch_enforcement.py
```

---

## Findings by Category

### 1. subprocess in Planning/Control/Orchestrator

**Result: CLEAN**

Zero matches. No subprocess usage in umh/planning/, umh/control/, or umh/orchestrator/. The planning layer is pure.

---

### 2. call_with_fallback Usage

**Result: CLEAN**

Matches found in:
- `umh/runtime_engine/model_router.py` (definition) -- sanctioned
- `umh/runtime_engine/agent_runtime.py` (deprecation shim pointing to router) -- sanctioned
- `umh/runtime_engine/voice_engine.py` (voice pipeline) -- sanctioned
- `umh/stages/llm_generation.py` (stage pipeline) -- sanctioned
- `umh/adapters/model_router.py` (adapter-layer router definition) -- sanctioned
- `umh/adapters/umh_execution.py` (SpineExecutionBackend) -- sanctioned
- `umh/runtime_engine/multi_strategy.py` (candidate generation) -- sanctioned
- `umh/substrate/voice_eos_responder.py` (voice responder) -- sanctioned
- `umh/substrate/meeting_intelligence.py` (meeting processor) -- sanctioned

**Zero matches in umh/planning/, umh/control/, or umh/orchestrator/.** No architectural violation.

---

### 3. Direct Adapter Imports Outside Execution Layer

**Result: FALSE_POSITIVE (all legitimate)**

Matches outside umh/execution/ and umh/adapters/:

| File | Import | Classification |
|------|--------|----------------|
| `umh/runtime_engine/model_router.py` | `from umh.adapters.model_router import ...` | FALSE_POSITIVE -- runtime_engine is the runtime layer, not planning/control. Model router re-export is the sanctioned path. |
| `umh/capability/registry.py` | `from umh.adapters.llm import discover_llm_adapter` | FALSE_POSITIVE -- capability registry discovers what adapters exist, does not invoke them. |
| `umh/runtime_loop/live_loop.py` | `from umh.adapters.registry import AdapterRegistry` | FALSE_POSITIVE -- runtime loop is the execution runtime, adapter registry access is expected. |
| `umh/runtime_loop/lifecycle.py` | `from umh.adapters.event_router import route_events` / `AdapterRegistry` | FALSE_POSITIVE -- lifecycle is runtime infrastructure. |
| `umh/goals/interfaces.py` | `from umh.adapters.bridge import discover_platform_adapter` | FALSE_POSITIVE -- discovery only, no execution. |
| `umh/protocols/workstation.py` | `from umh.adapters.base import WorkstationAdapter` | FALSE_POSITIVE -- protocol definition imports the base class (type only). |
| `umh/protocols/adapters.py` | `from umh.adapters.base import ...` | FALSE_POSITIVE -- protocol layer defines adapter interfaces. |
| `umh/strategy/interfaces.py` | `from umh.adapters.bridge import discover_platform_adapter` | FALSE_POSITIVE -- discovery only. |
| `umh/memory/storage.py` | `from umh.adapters.bridge import discover_platform_adapter` | FALSE_POSITIVE -- discovery only. |
| `umh/interfaces/cli.py` | `from umh.adapters.base import list_adapters, get_adapter` | FALSE_POSITIVE -- CLI is a user-facing surface, adapter listing is expected. |

**Zero adapter imports in umh/planning/, umh/control/, or umh/orchestrator/.** No violation.

---

### 4. shell=True

**Result: VIOLATION (2 instances in adapters)**

| File | Line | Classification |
|------|------|----------------|
| `umh/adapters/workstation_adapter.py:83` | `shell=True` in `_run_command()` | **VIOLATION** -- accepts `cmd: str` and passes to `subprocess.run(cmd, shell=True)`. The `cmd` comes from workspace config `cmd_entry`. If workspace config is attacker-controlled, this is command injection. |
| `umh/adapters/execution/workstation_adapter.py:83` | Identical duplicate | **VIOLATION** -- same code duplicated in execution subpackage. |
| `umh/substrate/station_daemon.py:513` | Comment states "never shell=True" | FALSE_POSITIVE -- the comment documents that shell=True is avoided. Actual `subprocess.Popen` call uses list argv. |
| `umh/interfaces/telegram/bot.py:258` | Comment says "No shell=True" | FALSE_POSITIVE -- documentation comment. |
| `umh/substrate/dispatch_enforcement.py:250` | `shell=False` (explicit) | FALSE_POSITIVE -- explicitly sets shell=False. Correct pattern. |

**Risk:** Medium. The workstation adapter's `_run_command` takes a string command and runs it with `shell=True`. The command comes from workspace config dicts. If config is user-controlled or loaded from external source, this is a shell injection vector.

**Required fix:** Convert to `shlex.split()` + `shell=False`, or route through `dispatch_enforcement.py` which already has proper allowlist enforcement with `shell=False`.

---

### 5. Dangerous System Calls

**Result: CLEAN**

Zero matches across all UMH code.

---

### 6. Hardcoded API Keys/Secrets

**Result: CLEAN**

Zero matches for hardcoded key patterns, token patterns (`sk-`, `AIza`, `ghp_`, `xoxb-`).

---

### 7. Approval Bypass

**Result: CLEAN (all legitimate patterns)**

| File | Match | Classification |
|------|-------|----------------|
| `umh/execution/engine.py:115` | `approved_execution = True` | FALSE_POSITIVE -- this is set ONLY after `store.validate_for_execution()` returns `valid=True`. The approval store validates the approval_id, operation, and capability type. If invalid, execution is DENIED (line 122-157). Correct pattern. |
| `umh/capabilities/spec.py:42` | `requires_approval: bool = False` | FALSE_POSITIVE -- default field on a capability spec dataclass. Capabilities that need approval set it to True. Default False is correct for PURE/LLM_CALL operations. |
| `umh/governance/capability.py:184` | `needs_approval: bool = False` | FALSE_POSITIVE -- same pattern, governance layer default. |
| `umh/substrate/operator_delivery.py:359` | `"is_approval": False` | FALSE_POSITIVE -- message metadata flag indicating the message is not an approval response. |
| `umh/substrate/runtime_mode.py:130` | `is_approval: bool = False` | FALSE_POSITIVE -- mode routing flag. |

No approval bypass found. The engine enforces approval checks for non-PURE/non-LLM_CALL execution classes at lines 99-256.

---

### 8. Environment/Sandbox Bypass

**Result: CLEAN (design-level default, not bypass)**

| File | Match | Classification |
|------|-------|----------------|
| `umh/control/api.py:131` | `sandbox: bool = False` | FALSE_POSITIVE -- field on `ExecuteBody` Pydantic model. This is the API request schema default. The execution engine enforces security via `execution_guard.py` regardless of this field. The `sandbox` field is a constraint hint, not a security gate bypass. |
| `umh/execution/contract.py:74` | `sandbox: bool = False` | FALSE_POSITIVE -- `ExecutionConstraints` dataclass default. Same reasoning. |
| `umh/substrate/execution_contract.py:72` | `sandbox: bool = False` | FALSE_POSITIVE -- duplicate contract in substrate. Same reasoning. |

No sandbox bypass. The actual security enforcement is in `umh/security/execution_guard.py` which checks path sandboxing, command allowlists, and dangerous characters independently of the `sandbox` field.

---

### 9. Plan Validation Before Execution

**Result: CLEAN**

The validation chain is correctly enforced:

1. **`umh/planning/planner.py:104`** -- `create_plan()` calls `validate_plan(plan)` immediately after plan creation. If validation fails, plan status is set to `REJECTED`.

2. **`umh/planning/planner.py:281-295`** -- `execute_plan()` requires `plan.status == PlanStatus.VALIDATED`. Cannot execute an unvalidated plan.

3. **`umh/control/api.py:527-531`** -- The `/plans/{plan_id}/execute` endpoint checks `plan.status != PlanStatus.VALIDATED` and returns 409 if not. Also checks quality verdict and blocks on `fail`.

4. **`umh/control/api.py:554-563`** -- Separate `/plans/{plan_id}/validate` endpoint exists for explicit re-validation.

No path exists to execute a plan without validation.

---

### 10. Task Execution Bypass

**Result: CLEAN**

The `execute()` calls in `umh/control/identity.py` are all SQLite `conn.execute()` -- database operations, not task execution. No relation to the UMH execution engine.

The orchestrator's `execute_task()` at `umh/orchestrator/task.py:173` correctly:
- Imports `from umh.execution.engine import execute`
- Builds `ExecutionRequest` objects for each step
- Calls `execute(request)` through the canonical engine
- Handles approval pausing when execution returns `requires_approval`

No bypass of the execution engine found.

---

### 11. subprocess in Adapters (Extended)

**Result: ACCEPTABLE with one exception noted in Finding 4**

| File | Usage | Classification |
|------|-------|----------------|
| `umh/adapters/umh_execution.py:160` | `subprocess.run(allowed, ...)` | CLEAN -- uses list `allowed` (not string), no `shell=True`. The `allowed` variable comes from `_SHELL_ALLOWLIST` after validation. |
| `umh/adapters/computer_use_adapter.py` (multiple) | `subprocess.run([...], ...)` | CLEAN -- all calls use list argv, no `shell=True` found in this file. |
| `umh/adapters/workstation_adapter.py:81` | See Finding 4 | VIOLATION |
| `umh/adapters/execution/workstation_adapter.py:81` | See Finding 4 | VIOLATION (duplicate) |

---

### 12. subprocess in substrate (Out of Primary Scope, Noted)

The substrate layer (`umh/substrate/`) has subprocess usage in:
- `station_daemon.py` -- uses list argv, explicitly documents "never shell=True"
- `os_controller.py` -- uses list argv, no shell=True
- `dispatch_enforcement.py` -- explicitly sets `shell=False`

All substrate subprocess calls follow correct patterns.

---

## Risk Classification Summary

| # | Check | Result | Risk |
|---|-------|--------|------|
| 1 | subprocess in planning/control/orchestrator | CLEAN | None |
| 2 | call_with_fallback misuse | CLEAN | None |
| 3 | Direct adapter imports outside execution | CLEAN | None |
| 4 | shell=True | **VIOLATION** (2 files) | Medium |
| 5 | Dangerous system calls | CLEAN | None |
| 6 | Hardcoded secrets | CLEAN | None |
| 7 | Approval bypass | CLEAN | None |
| 8 | Environment/sandbox bypass | CLEAN | None |
| 9 | Plan validation before execution | CLEAN | None |
| 10 | Task execution bypass | CLEAN | None |

---

## Required Fixes

### FIX-1: shell=True in workstation_adapter.py (MEDIUM)

**Files:**
- `umh/adapters/workstation_adapter.py:78-87`
- `umh/adapters/execution/workstation_adapter.py:78-87`

**Current:**
```python
def _run_command(cmd: str, label: str) -> bool:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
```

**Required:**
Convert to `shlex.split()` + `shell=False`, or route through `dispatch_enforcement.py` which already has proper allowlist enforcement with `shell=False`.

**Risk if not fixed:** If workspace config is loaded from external/user-controlled source, arbitrary shell command injection is possible.

---

## Architectural Observations

1. **Planning layer purity is confirmed.** Zero subprocess, zero adapter imports, zero call_with_fallback, zero direct LLM SDK imports. The planning layer is structurally clean.

2. **Control plane correctly delegates.** The control API routes plan execution through `planner.execute_plan()` which validates status and quality before converting to tasks. The task system routes through `execution.engine.execute()`.

3. **Orchestrator correctly routes through execution engine.** `orchestrator/task.py:execute_task()` builds `ExecutionRequest` objects and calls the canonical `execute()` function. No execution bypass.

4. **Security guard is properly positioned.** `umh/security/execution_guard.py` is invoked by `execution/engine.py` for all non-PURE/non-LLM_CALL operations. Approval flow is enforced with single-use consumption.

5. **Duplicate contract files.** `umh/execution/contract.py` and `umh/substrate/execution_contract.py` contain duplicate `ExecutionConstraints` dataclass definitions. Not a security issue but a maintenance risk.

---

## Overall Verdict: PASS

One medium-risk finding (`shell=True` in workstation adapter, 2 duplicate files). No high or critical violations. The core architectural boundaries -- planning purity, control plane delegation, execution engine gatekeeping, and approval enforcement -- are all intact and correctly wired.
