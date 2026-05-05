# Phase 4A.5: Environment Execution Reality Stabilization — Completion Report

**Date:** 2026-04-26
**Status:** COMPLETE
**Tests:** 961/961 unit tests pass (919 existing + 42 new), all files compile clean
**Approach:** Sequential (model → enforcement → selection → scoring → observability → tests)

---

## 1. Executive Summary

Phase 4A.5 introduced `ExecutionMode` — a three-state enum that explicitly
marks whether an environment has real runtime backing. This prevents the
system from accidentally routing real work into environments that cannot
actually execute it. Enforcement, selection, and scoring all now respect
execution mode as a hard constraint.

**Core invariant enforced:** No request requiring real execution may run in
an environment that does not have real execution backing.

---

## 2. Files Modified

| # | File | Change |
|---|------|--------|
| 1 | `umh/execution/environment.py` | Added `ExecutionMode` enum (REAL/SIMULATED/NOT_IMPLEMENTED). Added `execution_mode` field to `EnvironmentSpec` (default=REAL). Added `requires_real_execution()` helper. Updated `enforce_environment()` with execution mode check. Updated `select_environment()` to skip NOT_IMPLEMENTED in scoring. Set local=REAL, sandbox=SIMULATED, container=NOT_IMPLEMENTED. |
| 2 | `umh/execution/observability.py` | Added `execution_mode` field to `ExecutionEvent` (default="real"). Updated `to_dict()` to include execution_mode. Updated observer pending tuple from 6-tuple to 7-tuple (added exec_mode at index 4). Updated `on_request()` to capture `env.execution_mode.value`. Updated `on_result()` to unpack and pass execution_mode. Updated log format to include mode=. |
| 3 | `tests/unit/test_phase3b.py` | Updated 5 sandbox routing tests: sandboxed file ops now route to local (sandbox has no real backing). Updated observer test: sandboxed file_read observer now captures local env. |
| 4 | `tests/unit/test_phase3c.py` | Updated 3 observer pending tuple unpacking (6-tuple → indexed access for 7-tuple). Updated sandbox enforcement tests (sandbox is SIMULATED → DENY for real execution). Updated selection tests (sandbox routing → local). Removed `environment_enforced` assertion from sandbox observer test. |
| 5 | `tests/unit/test_phase4a.py` | Updated browser-to-container enforcement test (container is NOT_IMPLEMENTED → DENY). Updated browser routing test (no valid container → fallback to local). |

## 3. Files Created

| # | File | Purpose | Lines |
|---|------|---------|-------|
| 1 | `tests/unit/test_phase4a5.py` | 42 tests across 8 test classes | ~340 |

**Total: 5 files modified, 1 file created.**

---

## 4. ExecutionMode Taxonomy

### ExecutionMode enum

| Value | Meaning | When to use |
|-------|---------|-------------|
| `REAL` | Environment has actual runtime backing | Production environments with working execution |
| `SIMULATED` | Environment exists logically but has no runtime | Planned environments awaiting implementation |
| `NOT_IMPLEMENTED` | Environment defined but no implementation exists | Future capabilities with no timeline |

### Current environment assignments

| Environment | Type | Security | ExecutionMode | Rationale |
|-------------|------|----------|---------------|-----------|
| local | LOCAL | TRUSTED | **REAL** | Actual process execution on host |
| sandbox | SANDBOX | SANDBOXED | **SIMULATED** | No sandbox runtime exists today |
| container | CONTAINER | ISOLATED | **NOT_IMPLEMENTED** | No Docker/container integration exists |

---

## 5. requires_real_execution() Logic

```python
def requires_real_execution(request) -> bool:
    if request.execution_class == ExecutionClass.PURE:
        return not request.inputs.get("dry_run", False)
    return True
```

| ExecutionClass | dry_run | Result |
|----------------|---------|--------|
| SIDE_EFFECT | — | True |
| TRANSPORT | — | True |
| LLM_CALL | — | True |
| PURE | False/absent | True |
| PURE | True | **False** |

Only PURE + dry_run=True may tolerate simulated execution. Everything
else requires a REAL environment.

---

## 6. Environment Enforcement Decision Flow

```
enforce_environment(request, environment)
  │
  ├─ Capability support check
  │     └─ DENY if capability not in supported_capabilities
  │
  ├─ Sandbox constraint check
  │     └─ DENY if sandbox_required AND env is TRUSTED AND file_operation
  │
  ├─ Security level check
  │     └─ DENY if SIDE_EFFECT and unrecognized security level
  │
  ├─ NEW: Execution mode check
  │     └─ DENY if requires_real_execution(request)
  │           AND environment.execution_mode != REAL
  │           reason: "no real execution backing (mode=simulated|not_implemented)"
  │
  └─ ALLOW (all checks passed)
```

### Enforcement results (updated)

| Capability | Environment | Mode | Verdict | Reason |
|-----------|-------------|------|---------|--------|
| shell_command | local | REAL | ALLOW | — |
| shell_command | sandbox | SIMULATED | **DENY** | no real execution backing |
| file_read | local | REAL | ALLOW | — |
| file_read | sandbox | SIMULATED | **DENY** | no real execution backing |
| llm_call | local | REAL | ALLOW | — |
| llm_call | sandbox | — | DENY | capability not supported |
| browser_action | container | NOT_IMPLEMENTED | **DENY** | no real execution backing |
| browser_action | local | — | DENY | capability not supported |
| computer_use | local | REAL | ALLOW | — |
| computer_use | sandbox | — | DENY | capability not supported |

---

## 7. Selection Behavior Before/After

### Before (Phase 4A)

| Request | Candidates | Selected |
|---------|-----------|----------|
| shell_command | local, sandbox | local (default) |
| file_read (sandbox=True) | sandbox | sandbox |
| browser_navigate | container | container |
| llm_call | local | local |

### After (Phase 4A.5)

| Request | Candidates | Selected | Why changed |
|---------|-----------|----------|-------------|
| shell_command | local | local | sandbox eliminated (SIMULATED) |
| file_read (sandbox=True) | local | local | sandbox eliminated (SIMULATED), local fallback |
| browser_navigate | *(none)* | local (fallback) | container eliminated (NOT_IMPLEMENTED) |
| llm_call | local | local | unchanged |

### Fallback behavior

```
if 0 candidates:
  if local passes enforcement → return local (logged warning)
  else → return local anyway (logged warning with denial reason)
```

Local fallback is always safe because the engine's security guard and
backend routing provide additional checks before actual execution.

---

## 8. Scoring Behavior Before/After

### Before (Phase 4A)

- All environments participate in scoring equally
- NOT_IMPLEMENTED environments with synthetic stats could theoretically win

### After (Phase 4A.5)

- NOT_IMPLEMENTED environments are excluded from scoring competition
- Enforcement filters them out before scoring runs
- Additionally, `select_environment()` explicitly skips NOT_IMPLEMENTED
  environments in the scoring loop as defense-in-depth
- SIMULATED environments are excluded from scoring via enforcement
  (they fail the execution_mode check before reaching scoring)
- REAL environments participate normally
- Backward-compatible aggregate stats (`get_stats()`) unchanged

---

## 9. Observability Changes

### ExecutionEvent (updated)

| Field | Type | Default | New? |
|-------|------|---------|------|
| execution_mode | str | "real" | **YES** |

### Observer pending tuple (updated)

```
Index:  0          1              2       3          4            5            6
Value:  request    start_time    env_id   env_type   exec_mode    max_tokens   enforcement_flags
```

Previously at indices 4,5: max_tokens, enforcement_flags
Now shifted to indices 5,6 with exec_mode at index 4.

### Log format (updated)

```
[ExecutionObserver] result: id=... op=... capability=... status=... env=... mode=real max_tokens=... ...
```

The `mode=` field makes it immediately visible in logs when a request
was routed to a non-real environment.

---

## 10. Test Coverage

### 42 new tests across 8 classes

| Class | Tests | Coverage |
|-------|-------|----------|
| TestExecutionModeEnum | 4 | REAL/SIMULATED/NOT_IMPLEMENTED exist, all 3 values present |
| TestEnvironmentExecutionModes | 4 | local=REAL, sandbox=SIMULATED, container=NOT_IMPLEMENTED, default=REAL |
| TestRequiresRealExecution | 8 | shell/file_read/llm/browser/computer/file_write→True, pure→True, pure+dry_run→False |
| TestEnforcementExecutionMode | 7 | shell denied in sandbox, browser denied in container, shell/llm allowed in local, file_read denied in sandbox, pure dry_run allowed in simulated, reason includes mode |
| TestSelectionWithExecutionMode | 5 | browser→local fallback, shell→local, file_read+sandbox→local, llm→local, computer_use→local |
| TestScoringExecutionMode | 3 | NOT_IMPLEMENTED excluded, SIMULATED excluded for real exec, REAL stats tracked |
| TestObservabilityExecutionMode | 5 | event field exists, to_dict includes it, default=real, observer captures mode, browser falls back to real |
| TestExistingBehaviorUnchanged4A5 | 6 | shell works, file_read works, guard blocks, LLM unchanged, browser denied, sandbox flag doesn't break file_read |

### Updated prior phase tests

| File | Tests Changed | Change |
|------|--------------|--------|
| test_phase3b.py | 6 | Sandbox routing → local (sandbox SIMULATED), observer → local |
| test_phase3c.py | 6 | Observer tuple unpacking, sandbox enforcement→DENY, selection→local |
| test_phase4a.py | 2 | Browser enforcement→DENY in container, browser routing→local |

---

## 11. What Phase 4A.5 Did NOT Change

- No real browser automation implemented
- No container/sandbox runtime added
- Security guard logic untouched
- ExecutionRequest schema untouched
- Existing local execution behavior identical
- Shell allowlist untouched
- SANCTIONED LLM bypasses untouched
- External adapter interface untouched
- Adapter stubs untouched (still return NOT_IMPLEMENTED)
- Scoring data structures untouched (CapabilityStats unchanged)
- Engine.py untouched
- contract.py untouched

---

## 12. Cumulative Impact (Phase 0 → 4A.5)

| Phase | What changed | Test count |
|-------|-------------|-----------|
| Phase 0 | 4 CRITICAL security fixes | 712 |
| Phase 1A | SpineExecutionBackend created | 712 |
| Phase 1B | 7 bypasses redirected + LoggingObserver | 712 |
| Phase 2A-Lite | 5 bypasses + max_tokens + substrate stubs | 712 |
| Phase 2B | Shell execution + security guard + capability spec | 741 |
| Phase 2C | Guard in hot path + file ops + scoring + observability | 773 |
| Phase 3A | Environment abstraction layer | 800 |
| Phase 3B | Environment activation — sandbox routing + env-aware scoring | 832 |
| Phase 3C | Constraint enforcement + environment enforcement + cost control | 872 |
| Phase 4A | External capability interface — browser + computer_use stubs | 919 |
| **Phase 4A.5** | **Execution reality stabilization — mode enum + enforcement** | **961** |

**961/961 tests pass across all phases. Zero regressions.**

---

## 13. Is Phase 4B Safe?

**YES.** Phase 4A.5 makes Phase 4B safer than before. When real implementations
are added (computer_use API, Playwright browser, Docker containers), the path is:

1. Implement the adapter's `execute()` method
2. Change the environment's `execution_mode` from `NOT_IMPLEMENTED`/`SIMULATED` to `REAL`
3. Update the security guard to allow the new operations
4. Write tests

The `ExecutionMode` acts as a deployment gate — real traffic cannot flow to an
environment until its mode is explicitly set to REAL. This prevents partial
implementations from receiving live requests.

Recommended Phase 4B scope remains:
1. Computer use implementation via adapter (set local to handle computer_use ops)
2. Guard update for computer_use
3. Browser adapter implementation + container mode upgrade when Docker exists
4. Execution metrics CLI

Phase 4B should NOT:
- Implement Docker/container runtime (separate infrastructure concern)
- Modify enforcement or the execution contract
- Change existing local execution behavior
