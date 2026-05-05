# Phase 4C: Approval Flow + Execution Metrics CLI — Completion Report

**Date:** 2026-04-26
**Status:** COMPLETE
**Tests:** 1036/1036 unit tests pass (998 existing + 38 new), all files compile clean
**Approach:** Sequential (approval model → engine integration → adapter integration → metrics CLI → tests → validation)

---

## 1. Executive Summary

Phase 4C added the approval plumbing for gated mutation operations and an
execution metrics CLI. The engine now creates trackable ApprovalRequests
when the guard returns REQUIRES_APPROVAL, and the adapter checks for valid
approved approvals before proceeding (though actual mutation execution
remains NOT_IMPLEMENTED — plumbing only).

The metrics CLI (`python3 -m umh.execution.metrics`) surfaces the full
system status: capability map, environment status, scoring stats, and
pending approvals.

**The approval flow completes the REQUIRES_APPROVAL path through the
full pipeline: guard → engine (creates approval) → adapter (validates
approval) → result.**

---

## 2. Files Created

| # | File | Purpose | Lines |
|---|------|---------|-------|
| 1 | `umh/execution/approval.py` | ApprovalStatus enum, ApprovalRequest dataclass, thread-safe ApprovalStore | ~146 |
| 2 | `umh/execution/metrics.py` | Execution metrics CLI — capability/env/scoring/approval status | ~205 |
| 3 | `tests/unit/test_phase4c.py` | 38 tests across 6 test classes | ~540 |

## 3. Files Modified

| # | File | Change |
|---|------|--------|
| 1 | `umh/execution/engine.py` | Added REQUIRES_APPROVAL handling: creates ApprovalRequest, returns REJECTED with approval_id |
| 2 | `umh/adapters/computer_use_adapter.py` | Added `_handle_mutation()`: checks approval_id validity before attempting mutation |
| 3 | `tests/unit/test_phase4b.py` | Updated 2 tests: click/type now return `requires_approval` + `approval_id` (was `guard_denied`) |

**Total: 3 files created, 3 files modified.**

---

## 4. Approval Model

### ApprovalStatus enum

```python
class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
```

### ApprovalRequest dataclass

Fields: id, execution_id, operation, capability_type, risk_level, inputs_summary, created_at, expires_at, status.

- `is_expired()` — compares expires_at against UTC now
- `to_dict()` — serializes to dict for API/logging

### ApprovalStore

Thread-safe in-memory store with:
- `create_approval()` — generates unique id, sets TTL (default 300s)
- `approve()` / `deny()` — transitions status (checks expiry on approve)
- `get()` — retrieves with auto-expire check
- `list_pending()` — returns non-expired pending requests
- `reset()` — clears all (for tests)

Module-level singleton via `get_approval_store()`.

---

## 5. Engine Integration

### Before (Phase 4B)

```python
if guard_result.verdict != GuardVerdict.ALLOW:
    # All non-ALLOW → generic DENY
    result = ExecutionResult(..., outputs={"guard_denied": True, ...})
```

### After (Phase 4C)

```python
if guard_result.verdict == GuardVerdict.REQUIRES_APPROVAL:
    # Create trackable approval request
    approval = store.create_approval(...)
    result = ExecutionResult(
        ...,
        outputs={"requires_approval": True, "approval_id": approval.id, ...},
    )
    return result

if guard_result.verdict != GuardVerdict.ALLOW:
    # All other non-ALLOW → generic DENY
    result = ExecutionResult(..., outputs={"guard_denied": True, ...})
```

REQUIRES_APPROVAL is now handled as a distinct path: it creates an
ApprovalRequest and returns both the reason and the approval_id in the
result outputs. This enables future approval workflows.

---

## 6. Adapter Integration

### Mutation routing

```python
def execute(self, request, environment):
    ...
    if op in _MUTATION_OPS:
        return self._handle_mutation(request)  # was: self._requires_approval(request)
```

### _handle_mutation() flow

```
_handle_mutation(request)
  ├─ No approval_id in inputs → REJECTED (requires_approval)
  ├─ approval_id not found in store → REJECTED (requires_approval)
  ├─ approval status != APPROVED → REJECTED (requires_approval)
  └─ approval status == APPROVED → REJECTED (approved=True, not_implemented=True)
```

Even with a valid approved approval, mutations return NOT_IMPLEMENTED.
This is the plumbing phase — actual mutation execution requires a future
phase.

### Defense in depth (3 layers now)

1. **Guard level:** REQUIRES_APPROVAL → engine creates approval → REJECTED
2. **Adapter level:** checks approval_id → requires_approval if invalid
3. **Implementation level:** even if approved, returns NOT_IMPLEMENTED

---

## 7. Metrics CLI

### Usage

```bash
python3 -m umh.execution.metrics          # human-readable
python3 -m umh.execution.metrics --json   # structured JSON
```

### Sections

| Section | Source | Content |
|---------|--------|---------|
| Capability Status | `_capability_status_map()` | 8 capability entries with status/guard/env/adapter |
| Environments | `list_environments()` | 3 environments with type/security/mode/capabilities |
| Scoring (Aggregate) | `get_capability_scorer()` | Per-capability success/fail/timeout rates, latency, cost |
| Scoring (Per Env) | `get_capability_scorer()` | Same stats broken out by environment |
| Approvals | `get_approval_store()` | Pending count and pending request details |

### Sample output (human)

```
============================================================
UMH EXECUTION METRICS
============================================================

--- Capability Status ---
  llm_call             ACTIVE     12 operation types
  shell_command        ACTIVE     12 allowlisted
  file_operation       ACTIVE     read/list/stat
  file_operation       STUB       write/delete
  computer_use         ACTIVE     screenshot/screen_size/active_window
  computer_use         GATED      click/type/key/scroll/drag
  browser_action       STUB       navigate/click/type/screenshot/extract
  os_interaction       NOT_WIRED  *

--- Environments ---
  local        mode=real             security=trusted    caps=[computer_use, file_operation, llm_call, shell_command]
  sandbox      mode=simulated        security=sandboxed  caps=[file_operation, shell_command]
  container    mode=not_implemented  security=isolated   caps=[browser_action, shell_command]
```

---

## 8. Test Coverage

### 38 new tests across 6 classes

| Class | Tests | Coverage |
|-------|-------|----------|
| TestApprovalStoreCreate | 5 | create returns request, timestamps, default risk, custom TTL, to_dict |
| TestApprovalStoreActions | 10 | approve/deny/get/list_pending, unknown IDs return None, expiry, reset |
| TestEngineApprovalFlow | 5 | click/type/scroll → REJECTED with approval_id, approval in store, error text |
| TestAdapterMutationApproval | 4 | no approval_id → requires_approval, invalid → requires_approval, approved → not_implemented, denied → requires_approval |
| TestMetricsCLI | 9 | get_metrics dict structure, computer_use entries, ACTIVE/GATED statuses, environments list/fields, scoring structure, approvals, human/JSON output |
| TestExistingBehaviorUnchanged4C | 5 | LLM call, shell uptime, file read, computer_screenshot, unknown op denied |

### Updated prior phase tests

| File | Tests Changed | Change |
|------|--------------|--------|
| test_phase4b.py | 2 | click/type guard tests: `guard_denied` → `requires_approval` + `approval_id` |

---

## 9. What Phase 4C Did NOT Change

- No actual mutation execution implemented
- No Docker/container runtime
- No browser automation
- ExecutionRequest schema untouched
- ExecutionResult schema untouched
- Environment definitions untouched
- Shell allowlist untouched
- Scoring logic untouched
- Guard logic untouched (only engine handling of guard verdicts changed)
- No async or agent patterns added

---

## 10. Cumulative Impact (Phase 0 → 4C)

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
| **Phase 4C** | **Approval flow + execution metrics CLI** | **1036** |

**1036/1036 tests pass across all phases. Zero regressions.**

---

## 11. Capability Status Map (Full System — Post-4C)

| Capability | Operations | Status | Guard | Approval | Environment | Adapter |
|-----------|-----------|--------|-------|----------|-------------|---------|
| llm_call | 12 operation types | **ACTIVE** | — (bypass) | — | local (REAL) | built-in |
| shell_command | 12 allowlisted | **ACTIVE** | allowlist + metachar | — | local (REAL) | built-in |
| file_operation | read/list/stat | **ACTIVE** | path sandbox | — | local (REAL) | built-in |
| file_operation | write/delete | STUB | path sandbox | — | local (REAL) | built-in |
| **computer_use** | **screenshot/screen_size/active_window** | **ACTIVE** | **read-only ALLOW** | **—** | **local (REAL)** | **computer_use_adapter** |
| **computer_use** | **click/type/key/scroll/drag** | **GATED** | **REQUIRES_APPROVAL** | **ApprovalStore** | **local (REAL)** | **computer_use_adapter** |
| browser_action | navigate/click/type/screenshot/extract | STUB | DENY | — | container (NOT_IMPL) | browser_adapter |
| os_interaction | * | NOT WIRED | DENY | — | — | — |

---

## 12. Approval Flow Architecture

```
execute(request: computer_click)
  │
  ├─ observer.on_request()
  │
  ├─ security guard
  │     └─ check_computer_operation("computer_click")
  │     └─ → REQUIRES_APPROVAL
  │
  ├─ engine handles REQUIRES_APPROVAL    ← NEW
  │     └─ ApprovalStore.create_approval()
  │     └─ returns REJECTED {requires_approval, approval_id, reason}
  │
  └─ observer.on_result()


# Future: approved retry path (not yet implemented)
execute(request: computer_click, inputs={approval_id: "approval_xxx"})
  │
  ├─ guard → REQUIRES_APPROVAL → engine creates new approval
  │   (guard doesn't see approval_id, it only checks operation type)
  │
  # To skip the guard for approved retries, a future phase would need
  # to add approval_id awareness to the guard or engine pre-check.
```

---

## 13. Is Phase 4D Safe?

**YES.** Recommended Phase 4D scope:

1. **Approved retry path** — allow approved mutations to bypass the guard
   and reach the adapter for execution (requires guard or engine pre-check)
2. **Actual mutation implementation** — implement click/type/key using
   xdotool or similar on the Xvfb display
3. **Approval API** — expose approve/deny/list via gateway for external
   approval workflows

Phase 4D should NOT:
- Implement Docker/container runtime (infrastructure concern)
- Modify the execution contract
- Change enforcement architecture
- Add async or agent patterns
