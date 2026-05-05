# Phase 3C: Constraint Enforcement + Environment Enforcement + Cost Control + Scoring Activation — Completion Report

**Date:** 2026-04-26
**Status:** COMPLETE
**Tests:** 872/872 unit tests pass (832 existing + 40 new), all files compile clean
**Approach:** Sequential (enforcement → scoring → observability → call sites → tests)

---

## 1. Executive Summary

Phase 3C upgraded the system from environment-aware to environment-enforced
execution. Every request now passes through `enforce_environment()` before
execution — a hard check that the selected environment supports the
requested capability and satisfies sandbox constraints. The scorer gained
timeout and failure rate tracking. max_tokens is now applied at all critical
call sites (email_gps, decision_log, quality_gate). The observer captures
enforcement flags and max_tokens in every ExecutionEvent.

**The system now actively prevents constraint violations rather than merely
reporting on them.**

---

## 2. Files Created

| # | File | Purpose | Lines |
|---|------|---------|-------|
| 1 | `tests/unit/test_phase3c.py` | 40 tests across 8 test classes | ~400 |

## 3. Files Modified

| # | File | Change |
|---|------|--------|
| 1 | `umh/execution/environment.py` | Added `EnforcementVerdict`, `EnforcementResult`, `_classify_capability()`, `enforce_environment()`. Updated `select_environment()` with multi-candidate filtering, enforcement checks, scoring with cold-start protection (min 5 calls), and LOCAL fallback. |
| 2 | `umh/execution/scoring.py` | Added `timed_out_calls` field, `failure_rate` and `timeout_rate` properties to `CapabilityStats`. Updated `_record_into()` to distinguish `timed_out` from `failed`. Updated `to_dict()` with new fields. |
| 3 | `umh/execution/observability.py` | Added `max_tokens` and `enforcement_flags` fields to `ExecutionEvent`. Updated `EnhancedExecutionObserver._pending` to 6-tuple. Observer now captures max_tokens, sandbox, cost_limit, and enforcement verification in flags. Log lines include `max_tokens=`. |
| 4 | `umh/runtime_engine/email_gps.py` | Applied max_tokens: `email_gps_purpose=100`, `email_gps_classify=50`, `email_gps_draft=200`, `email_gps_extract=200` |
| 5 | `umh/runtime_engine/decision_log.py` | Applied max_tokens: `decision_log_extract=150` |
| 6 | `umh/runtime_engine/quality_gate.py` | Applied max_tokens: `quality_gate_check=500` |
| 7 | `tests/unit/test_phase3a.py` | Updated observer pending tuple unpacking (4 → 6 elements) |
| 8 | `tests/unit/test_phase3b.py` | Updated observer pending tuple unpacking (4 → 6 elements) |

**Total: 1 file created, 8 files modified.**

---

## 4. Environment Enforcement Layer

### enforce_environment() — Decision Flow

```
enforce_environment(request, environment)
  │
  ├─ capability = _classify_capability(request)
  │
  ├─ IF capability NOT in environment.supported_capabilities
  │     → DENY: "does not support capability"
  │
  ├─ IF request.constraints.sandbox
  │   AND environment.security_level == TRUSTED
  │   AND operation is file operation
  │     → DENY: "sandbox required but environment is trusted"
  │
  ├─ IF execution_class == SIDE_EFFECT
  │   AND security_level NOT in {TRUSTED, SANDBOXED, ISOLATED}
  │     → DENY: "side-effect requires recognized security level"
  │
  └─ → ALLOW
```

### Enforcement Rules Summary

| Condition | Rule | Effect |
|-----------|------|--------|
| Capability support | Environment must support the classified capability | Blocks LLM in sandbox |
| Sandbox constraint | sandbox=True requires non-TRUSTED security level for file ops | Blocks file ops in local when sandbox requested |
| Side-effect safety | SIDE_EFFECT requires recognized SecurityLevel | Blocks unknown security levels |

---

## 5. Updated Environment Selection

### select_environment() — Pipeline

```
select_environment(request)
  │
  ├─ 1. classify capability
  │
  ├─ 2. for each registered environment:
  │       enforce_environment(request, env)
  │       keep if ALLOW
  │
  ├─ 3. IF 0 candidates → fallback to LOCAL (logged)
  │
  ├─ 4. IF 1 candidate → return it
  │
  ├─ 5. IF sandbox requested + file op → prefer SANDBOX
  │
  ├─ 6. IF scoring has data (≥5 calls per env):
  │       score = success_rate × 1000 − avg_latency_ms
  │       pick highest score
  │
  └─ 7. DEFAULT: prefer LOCAL among candidates
```

### Cold-start protection

Scoring requires **minimum 5 calls** per environment before influencing
selection. With fewer calls, a single success/failure would swing the rate
too dramatically. This prevents unstable routing during initial execution.

### Scoring safety invariant

**Scoring NEVER overrides enforcement.** The scoring step only runs on
candidates that already passed `enforce_environment()`. A high-scoring
environment that violates a constraint is never considered.

---

## 6. max_tokens Enforcement

### Call site values (before → after)

| Call site | Operation | Before | After |
|-----------|-----------|--------|-------|
| `email_gps.py` | `email_gps_purpose` | 1024 (default) | **100** |
| `email_gps.py` | `email_gps_classify` | 1024 (default) | **50** |
| `email_gps.py` | `email_gps_draft` | 1024 (default) | **200** |
| `email_gps.py` | `email_gps_extract` | 1024 (default) | **200** |
| `decision_log.py` | `decision_log_extract` | 1024 (default) | **150** |
| `quality_gate.py` | `quality_gate_check` | 1024 (default) | **500** |

### Propagation path

```
utility_llm_call(prompt, max_tokens=50)
  → lightweight_execute(max_tokens=50)
    → ExecutionRequest(constraints=ExecutionConstraints(max_tokens=50))
    → execute(request)
      → observer.on_request()  ← captures max_tokens in pending + enforcement_flags
      → backend._execute_llm()
        → call_with_fallback(max_tokens=50)  ← enforced at LLM SDK level
      → observer.on_result()  ← max_tokens in ExecutionEvent
```

### Cost impact estimate

| Operation | Old max_tokens | New max_tokens | Reduction |
|-----------|---------------|----------------|-----------|
| email_gps_classify | 1024 | 50 | **95%** |
| email_gps_purpose | 1024 | 100 | **90%** |
| email_gps_draft | 1024 | 200 | **80%** |
| email_gps_extract | 1024 | 200 | **80%** |
| decision_log_extract | 1024 | 150 | **85%** |
| quality_gate_check | 1024 | 500 | **51%** |

These are output token budget reductions. Actual cost savings depend on how
much of the budget was being consumed — but the cap prevents runaway outputs.

---

## 7. Scoring Enhancements

### CapabilityStats — new fields

| Field | Type | Description |
|-------|------|-------------|
| `timed_out_calls` | int | Executions with status=timed_out |
| `failure_rate` | property → float | failed_calls / total_calls |
| `timeout_rate` | property → float | timed_out_calls / total_calls |

### Timeout counting

`timed_out` status increments **both** `timed_out_calls` AND `failed_calls`.
This is intentional — a timeout is a type of failure, so `failure_rate`
includes timeouts. `timeout_rate` isolates the timeout-specific subset.

### to_dict() output (new)

```python
{
    "total_calls": 10,
    "successful_calls": 7,
    "failed_calls": 3,
    "rejected_calls": 0,
    "timed_out_calls": 1,     # NEW
    "success_rate": 0.7,
    "failure_rate": 0.3,      # NEW
    "timeout_rate": 0.1,      # NEW
    "avg_latency_ms": 42.5,
    "total_cost_usd": 0.015,
    "last_error": "...",
}
```

---

## 8. ExecutionEvent — Updated Fields

| Field | Type | Phase added |
|-------|------|-------------|
| execution_id | str | 2C |
| operation | str | 2C |
| capability_type | str | 2C |
| execution_class | str | 2C |
| status | str | 2C |
| latency_ms | int | 2C |
| model_used | str | 2C |
| cost_usd | float | 2C |
| error | str | 2C |
| issued_by | str | 2C |
| adapter | str | 2C |
| environment_id | str | 3A |
| environment_type | str | 3A |
| **max_tokens** | **int** | **3C** |
| **enforcement_flags** | **tuple[str, ...]** | **3C** |

### enforcement_flags values

| Flag | When set |
|------|----------|
| `sandbox_requested` | `constraints.sandbox == True` |
| `max_tokens=N` | `constraints.max_tokens > 0` |
| `cost_limit=$X.XXXX` | `constraints.cost_limit_usd > 0` |
| `environment_enforced` | `enforce_environment()` returned ALLOW |

---

## 9. Observer — Updated Log Format

**Before (Phase 3B):**
```
[ExecutionObserver] request: id=X op=utility class=llm_call capability=llm_call env=local issued_by=test
[ExecutionObserver] result: id=X op=utility capability=llm_call status=succeeded env=local model=test latency=5ms cost=$0.001000
```

**After (Phase 3C):**
```
[ExecutionObserver] request: id=X op=utility class=llm_call capability=llm_call env=local max_tokens=50 issued_by=test
[ExecutionObserver] result: id=X op=utility capability=llm_call status=succeeded env=local max_tokens=50 model=test latency=5ms cost=$0.001000
```

One field added to each log line. No format breaking changes.

---

## 10. Test Coverage

### 40 new tests across 8 classes

| Class | Tests | Coverage |
|-------|-------|----------|
| TestEnforceEnvironment | 8 | LLM in local (allow), LLM in sandbox (deny), file_read no sandbox (allow), sandboxed file_read in local (deny), sandboxed file_read in sandbox (allow), shell in local/sandbox (allow), unsupported capability (deny) |
| TestUpdatedSelectEnvironment | 6 | LLM→local, file→local, file+sandbox→sandbox, shell→local, scoring doesn't override enforcement, scoring used with data |
| TestMaxTokensPropagation | 5 | Constraints carry max_tokens, lightweight_execute passes to call_with_fallback, event has max_tokens/enforcement_flags, defaults |
| TestMaxTokensAtCallSites | 6 | Source-level verification: email_gps (4 ops), decision_log (1), quality_gate (1) |
| TestScoringEnhancements | 6 | timed_out tracking, timeout_rate, failure_rate, env timeout_rate, to_dict new fields, cost per environment |
| TestObserverEnforcement | 4 | Observer captures max_tokens, sandbox flag, cost_limit, defaults without request |
| TestExecutionBehaviorUnchanged3C | 5 | Shell works, file_read works, guard blocks, LLM unchanged, sandboxed file_read works |

### Updated prior phase tests

| File | Change |
|------|--------|
| `test_phase3a.py` | Updated pending tuple unpacking (4 → indexed access) |
| `test_phase3b.py` | Updated pending tuple unpacking (4 → indexed access) |

---

## 11. What Phase 3C Did NOT Change

- ExecutionRequest schema — untouched
- ExecutionResult schema — untouched
- Security guard — untouched
- Shell allowlist — untouched
- Backend execution methods — untouched
- SANCTIONED LLM bypasses — untouched
- Docker/container execution — not introduced

---

## 12. Environment Selection Decision Flow (Summary)

```
                    ┌───────────────────────┐
                    │   ExecutionRequest     │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │ _classify_capability() │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │ For each environment:  │
                    │ enforce_environment()  │──── DENY → filtered out
                    └───────────┬───────────┘
                                │ (only ALLOW pass)
                                │
                    ┌───────────▼───────────┐
                    │ 0 candidates?         │──── YES → fallback LOCAL
                    └───────────┬───────────┘
                                │ NO
                    ┌───────────▼───────────┐
                    │ 1 candidate?          │──── YES → return it
                    └───────────┬───────────┘
                                │ NO (multiple)
                    ┌───────────▼───────────┐
                    │ sandbox + file_op?    │──── YES → prefer SANDBOX
                    └───────────┬───────────┘
                                │ NO
                    ┌───────────▼───────────┐
                    │ Scoring (≥5 calls)?   │──── YES → highest score wins
                    └───────────┬───────────┘
                                │ NO (insufficient data)
                    ┌───────────▼───────────┐
                    │ Default: prefer LOCAL  │
                    └───────────────────────┘
```

---

## 13. Scoring → Selection Behavior

| Scenario | Scoring influence | Result |
|----------|-------------------|--------|
| LLM call, only local supports it | None (1 candidate) | local |
| File op, sandbox=True | None (enforcement filters to 1) | sandbox |
| File op, sandbox=False | Only if ≥5 calls in both envs | local (default) |
| Shell command, both envs valid | Only if ≥5 calls in both envs | Highest score or local |
| Shell command, sandbox has 100% success, local has 80% | Scoring picks sandbox | sandbox |
| Shell command, sandbox has 100% but <5 calls | Cold-start protection | local |

**Safety invariant:** Scoring can never select an environment that failed
enforcement. It only ranks among already-validated candidates.

---

## 14. Cumulative Impact (Phase 0 → 3C)

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
| Phase 3C | Constraint enforcement + environment enforcement + cost control + scoring activation | 872 |

**872/872 tests pass across all phases. Zero regressions.**

---

## 15. Is Phase 4 Safe?

**YES.** Recommended Phase 4 scope:

1. **Execution metrics endpoint** — surface `get_all_env_stats()` via a CLI command or HTTP endpoint for operational dashboards
2. **Cost alerting** — use `cost_limit_usd` constraint to reject executions that would exceed budget (currently tracked but not enforced)
3. **Container environment stub** — define `_CONTAINER_ENV` for future isolated shell execution
4. **Duplicate reconciliation** — Phase 2 of reconciliation map: delete identical copies with 1-2 importers to fix

Phase 4 should NOT:
- Implement container/sandbox runtimes (actual process isolation)
- Modify the security guard or engine architecture
- Change existing capability behavior
- Touch sanctioned LLM bypasses
