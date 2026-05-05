# Phase 4D: Approved Execution Path + Guard Bypass Layer — Completion Report

**Date:** 2026-04-27
**Status:** COMPLETE
**Tests:** 1072/1072 unit tests pass (1036 existing + 36 new), all files compile clean
**Approach:** Sequential (approval model extensions → engine pre-guard check → guard bypass → adapter mutation implementations → observability → metrics → tests → validation)

---

## 1. Executive Summary

Phase 4D makes approved mutation operations executable without weakening
enforcement guarantees. The engine now validates approvals BEFORE the guard
runs, threads an `approved_execution` flag through the context, and the guard
allows approved known mutations to pass. The adapter executes all 5 mutation
operations via xdotool on the Xvfb display. Approvals are consumed after
successful execution, preventing replay attacks.

**Computer use mutations are now LIVE. The system can click, type, press keys,
scroll, and drag on the virtual display — but ONLY with explicit approval.**

### Success Condition Proof

```
execute(computer_click WITHOUT approval)
→ REJECTED, returns approval_id

approve(approval_id)

execute(computer_click WITH approval_id)
→ SUCCEEDED, xdotool actually clicked at (640,360)

execute(computer_click WITH SAME approval_id)
→ REJECTED, "already consumed"

execute(computer_click WITH WRONG approval)
→ REJECTED, "operation mismatch"
```

---

## 2. Control Flow — BEFORE vs AFTER

### BEFORE (Phase 4C)

```
execute(request: computer_click)
  │
  ├─ observer.on_request()
  │
  ├─ guard: check_execution("computer_click")
  │     └─ → REQUIRES_APPROVAL
  │
  ├─ engine: create approval → return REJECTED
  │     └─ {requires_approval, approval_id, reason}
  │
  └─ (no execution path even with approval)
```

### AFTER (Phase 4D)

```
execute(request: computer_click, inputs={approval_id: "approval_xxx"})
  │
  ├─ observer.on_request()
  │
  ├─ PRE-GUARD: approval validation                         ← NEW
  │     ├─ lookup approval_id in ApprovalStore
  │     ├─ validate: status==APPROVED, not expired
  │     ├─ validate: operation matches, capability matches
  │     ├─ IF valid → set approved_execution=True
  │     └─ IF invalid → REJECTED {approval_invalid, reason}
  │
  ├─ CONTEXT INJECTION                                       ← NEW
  │     └─ approved_execution=True + approval_id → context.metadata
  │
  ├─ guard: check_execution("computer_click", approved_execution=True)
  │     └─ → ALLOW (approved bypass)                         ← CHANGED
  │
  ├─ backend.execute()
  │     └─ adapter.execute()
  │         └─ context.metadata["approved_execution"] → True
  │         └─ _execute_mutation() → _click()                ← NEW
  │             └─ xdotool mousemove + click
  │             └─ → SUCCEEDED {x, y, button, adapter}
  │
  ├─ POST-EXECUTION: consume approval                        ← NEW
  │     └─ if SUCCEEDED → store.consume(approval_id)
  │     └─ status → CONSUMED (single-use)
  │
  └─ observer.on_result()
        └─ event.approved_execution=True
        └─ event.approval_id="approval_xxx"
```

---

## 3. Files Created

| # | File | Purpose | Lines |
|---|------|---------|-------|
| 1 | `tests/unit/test_phase4d.py` | 36 tests across 10 test classes | ~540 |

## 4. Files Modified

| # | File | Change |
|---|------|--------|
| 1 | `umh/execution/approval.py` | Added CONSUMED status, `consume()`, `validate_for_execution()`, `get_counters()`, lifecycle counters |
| 2 | `umh/execution/engine.py` | Added pre-guard approval check, context injection, post-execution consume |
| 3 | `umh/security/execution_guard.py` | Added `approved_execution` parameter, bypass for known computer mutations |
| 4 | `umh/adapters/computer_use_adapter.py` | Replaced `_handle_mutation` with 5 real xdotool implementations |
| 5 | `umh/execution/observability.py` | Added `approval_id` and `approved_execution` fields to ExecutionEvent |
| 6 | `umh/execution/metrics.py` | Added approval lifecycle counters, updated mutation status to ACTIVE (approved) |
| 7 | `tests/unit/test_phase4c.py` | Updated 2 tests for new adapter/metrics behavior |
| 8 | `docs/audits/phase4d_approved_execution_report.md` | This report |

**Total: 1 file created, 7 files modified.**

---

## 5. Approval Bypass Rules

The guard bypass is extremely narrow:

| Condition | Guard Behavior |
|-----------|---------------|
| `approved_execution=True` AND op in `_MUTATION_COMPUTER_OPS` | **ALLOW** |
| `approved_execution=True` AND unknown computer_* op | **DENY** (unchanged) |
| `approved_execution=True` AND shell_command | Normal allowlist check (unchanged) |
| `approved_execution=True` AND browser_* | **DENY** (unchanged) |
| `approved_execution=False` AND mutation op | **REQUIRES_APPROVAL** (unchanged) |
| Any non-computer mutation | Unaffected by approved_execution flag |

**Only known computer mutation operations can be bypassed, and only with a validated approval.**

---

## 6. Approval Binding Integrity

Before the guard bypass is triggered, the engine validates:

| Check | Failure Mode |
|-------|-------------|
| Approval exists in store | "not found" → REJECTED |
| Approval not expired | "has expired" → REJECTED |
| Approval status == APPROVED | "status is {status}" → REJECTED |
| Approval not consumed | "already consumed" → REJECTED |
| Approval.operation == request.operation | "operation mismatch" → REJECTED |
| Approval.capability_type == request capability | "capability mismatch" → REJECTED |

All 6 checks must pass. Any failure returns REJECTED with `approval_invalid=True`.

---

## 7. Mutation Execution Implementations

| Operation | xdotool Command | Output Fields |
|-----------|----------------|---------------|
| `computer_click` | `mousemove x y` + `click button` | x, y, button, adapter |
| `computer_type` | `type --clearmodifiers text` | chars_typed, adapter |
| `computer_key` | `key combo` | key, adapter |
| `computer_scroll` | `click 4/5` × n (4=up, 5=down) | direction, clicks, adapter |
| `computer_drag` | `mousemove` + `mousedown 1` + `mousemove` + `mouseup 1` | x1, y1, x2, y2, adapter |

All implementations:
- Use `subprocess.run()` with `capture_output=True` and `timeout=5`
- Return `FAILED` on any exception (never raise)
- Log operation details on success and failure
- Include timing via `now_ms()` differential

---

## 8. Replay Protection

```
execute(click, approval_id=X) → SUCCEEDED
  └─ engine calls store.consume(X)
  └─ approval X status → CONSUMED

execute(click, approval_id=X) → REJECTED
  └─ validate_for_execution(X, ...) → False, "already consumed"
  └─ result: {approval_invalid: True, reason: "already consumed"}
```

Approval lifecycle: `PENDING → APPROVED → CONSUMED` (terminal).
An approval can only be consumed once. After that, the store returns
"already consumed" for any reuse attempt.

---

## 9. Observability Extension

### New ExecutionEvent fields

| Field | Type | Default |
|-------|------|---------|
| `approval_id` | `str | None` | `None` |
| `approved_execution` | `bool` | `False` |

### Log format

Before (Phase 4C):
```
[ExecutionObserver] result: ... env=local mode=real max_tokens=0 ...
```

After (Phase 4D, approved execution):
```
[ExecutionObserver] result: ... env=local mode=real approved=True approval_id=approval_xxx max_tokens=0 ...
```

---

## 10. Metrics CLI Extension

### New approval counters

```
--- Approvals (pending=0) ---
  consumed=3 denied=1 expired=2
```

JSON output includes:
```json
"approvals": {
    "pending_count": 0,
    "pending": [],
    "approvals_consumed": 3,
    "approvals_denied": 1,
    "approvals_expired": 2
}
```

### Updated capability status

```
computer_use         ACTIVE (approved) click/type/key/scroll/drag
```

---

## 11. Test Coverage

### 36 new tests across 10 classes

| Class | Tests | Coverage |
|-------|-------|----------|
| TestApprovedExecution | 6 | click/type/key/scroll/drag succeed, adapter field present |
| TestNonApprovedPath | 2 | click/type without approval → REQUIRES_APPROVAL |
| TestInvalidApproval | 5 | wrong op, expired, nonexistent, pending, wrong capability → DENIED |
| TestReplayPrevention | 2 | consumed approval reuse → DENIED, status is CONSUMED |
| TestGuardIntegrity | 8 | screenshot ALLOW, unknown DENY, mutation REQUIRES_APPROVAL, approved flag bypass, approved doesn't bypass unknown/shell/browser |
| TestApprovalCounters | 4 | consumed/denied/expired counters, reset clears |
| TestApprovalObservability | 2 | event has approval fields, defaults correct |
| TestMetricsExtension | 2 | counters in metrics, status updated |
| TestExistingBehaviorUnchanged4D | 5 | LLM/shell/screenshot/unknown/file_read unchanged |

### Updated prior phase tests

| File | Tests Changed | Change |
|------|--------------|--------|
| test_phase4c.py | 2 | adapter test: checks `approved_execution` in context not `approval_id` in inputs; metrics: `GATED` → `ACTIVE (approved)` |

---

## 12. Defense in Depth (4 Layers)

| Layer | What it checks | Failure mode |
|-------|---------------|-------------|
| **1. Engine pre-guard** | Approval exists, valid, matches operation | REJECTED (approval_invalid) |
| **2. Guard** | approved_execution flag, operation type | REQUIRES_APPROVAL or DENY |
| **3. Adapter** | context.metadata["approved_execution"] | requires_approval |
| **4. Post-execution** | Consumes approval on success | Prevents replay |

Even if layers 1-2 were bypassed (impossible without code modification),
layer 3 independently checks the approval flag in context metadata.
Layer 4 ensures single-use regardless of other layers.

---

## 13. What Phase 4D Did NOT Change

- ExecutionRequest schema unchanged (uses metadata dict, not new fields)
- ExecutionResult schema unchanged
- Environment definitions unchanged
- Shell allowlist unchanged
- File operation guard unchanged
- Browser guard unchanged (still DENY)
- No Docker/container runtime
- No async or agent patterns
- Scoring logic unchanged

---

## 14. Cumulative Impact (Phase 0 → 4D)

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
| Phase 4A.5 | Execution reality stabilization — mode enum + enforcement | 961 |
| Phase 4B | Computer use adapter activation — first real external capability | 998 |
| Phase 4C | Approval flow + execution metrics CLI | 1036 |
| **Phase 4D** | **Approved execution path — mutations are LIVE** | **1072** |

**1072/1072 tests pass across all phases. Zero regressions.**

---

## 15. Capability Status Map (Full System — Post-4D)

| Capability | Operations | Status | Guard | Approval | Environment | Adapter |
|-----------|-----------|--------|-------|----------|-------------|---------|
| llm_call | 12 operation types | **ACTIVE** | — (bypass) | — | local (REAL) | built-in |
| shell_command | 12 allowlisted | **ACTIVE** | allowlist + metachar | — | local (REAL) | built-in |
| file_operation | read/list/stat | **ACTIVE** | path sandbox | — | local (REAL) | built-in |
| file_operation | write/delete | STUB | path sandbox | — | local (REAL) | built-in |
| computer_use | screenshot/screen_size/active_window | **ACTIVE** | read-only ALLOW | — | local (REAL) | computer_use_adapter |
| **computer_use** | **click/type/key/scroll/drag** | **ACTIVE (approved)** | **approved bypass** | **ApprovalStore** | **local (REAL)** | **computer_use_adapter** |
| browser_action | navigate/click/type/screenshot/extract | STUB | DENY | — | container (NOT_IMPL) | browser_adapter |
| os_interaction | * | NOT WIRED | DENY | — | — | — |
