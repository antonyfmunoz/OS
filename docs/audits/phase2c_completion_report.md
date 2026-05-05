# Phase 2C: Control, Safety, and Read-Only Capability Activation — Report

**Date:** 2026-04-26
**Status:** COMPLETE
**Tests:** 773/773 unit tests pass (741 existing + 32 new), all files compile clean
**Agents:** 4 parallel (security integration, file operations, observability/scoring, test coverage) + 1 direct (orphan cleanup)

---

## 1. Executive Summary

Phase 2C enforced security in the execution hot path, activated read-only file
operations, added structured observability with capability scoring, and deleted
2 orphaned duplicate files. The security guard now blocks dangerous operations
at the `execute()` level before they reach the backend. File reads, directory
listings, and stat operations work within the sandbox. Every execution produces
a structured `ExecutionEvent` and feeds per-capability performance statistics.

**The system has transitioned from "multi-capability engine" to "security-enforced
multi-capability engine with operational visibility."**

---

## 2. Files Created

| # | File | Purpose | Lines |
|---|------|---------|-------|
| 1 | `umh/execution/observability.py` | ExecutionEvent dataclass, _classify_capability(), EnhancedExecutionObserver | 148 |
| 2 | `umh/execution/scoring.py` | CapabilityStats, CapabilityScorer (thread-safe singleton), get_capability_scorer() | 118 |
| 3 | `tests/unit/test_phase2c.py` | 31 tests: guard integration (7), file ops (10), scoring (8), observability (5) + 1 from capabilities update | ~400 |

## 3. Files Modified

| # | File | Change |
|---|------|--------|
| 1 | `umh/execution/engine.py` | Added security guard check in `execute()` — blocks SIDE_EFFECT/TRANSPORT with DENY/REQUIRES_APPROVAL verdicts before backend dispatch |
| 2 | `umh/adapters/umh_execution.py` | Added `_execute_file_read()`, `_execute_list_dir()`, `_execute_stat_file()`. Updated `_execute_side_effect()` routing. Factory now returns `EnhancedExecutionObserver`. |
| 3 | `umh/capabilities/spec.py` | Added `FILE_OPERATION` to `_IMPLEMENTED_CAPABILITIES` |
| 4 | `umh/security/execution_guard.py` | Added `file_stat` to recognized file operations in `check_execution()` |
| 5 | `tests/unit/test_execution_capabilities.py` | Updated not-implemented tests (file_read is now implemented; tests cover file_write/file_delete instead) |

## 4. Files Deleted

| # | File | Reason |
|---|------|--------|
| 1 | `umh/policy/regime_engine.py` | Byte-identical orphan — 0 importers. Canonical copy: `umh/runtime_engine/regime_engine.py` |
| 2 | `umh/policy/risk_model.py` | Byte-identical orphan — 0 importers. Canonical copy: `umh/runtime_engine/risk_model.py` |

**Total: 3 files created, 5 files modified, 2 files deleted.**

---

## 3. Security Guard Integration

### Before Phase 2C

```
execute(request)
  → observer.on_request()
  → backend.execute()        ← no security check
  → observer.on_result()
```

### After Phase 2C

```
execute(request)
  → observer.on_request()
  → IF execution_class is SIDE_EFFECT or TRANSPORT:
      → check_execution(operation, inputs)
      → IF verdict != ALLOW: return REJECTED immediately
  → backend.execute()        ← only reached if guard allows
  → observer.on_result()
```

### Guard bypass rules

| ExecutionClass | Guard checked? | Reason |
|----------------|---------------|--------|
| PURE | No | No side effects — safe by definition |
| LLM_CALL | No | LLM calls go through model_router's own safety |
| SIDE_EFFECT | **Yes** | Shell commands, file ops, browser, OS |
| TRANSPORT | **Yes** | Network operations |

### Defense-in-depth layers

1. **Engine guard** (`execute()`) — blocks metacharacters, out-of-sandbox paths
2. **Backend allowlist** (`_execute_shell()`) — only 12 commands execute
3. **Backend file guard** (`_execute_file_read()` etc.) — calls `check_file_operation()` again
4. **No shell=True** — subprocess uses argv lists only

---

## 4. File Operations

### Implemented (read-only)

| Operation | Method | Sandbox enforced | What it returns |
|-----------|--------|-----------------|-----------------|
| `file_read` | `_execute_file_read()` | Yes | `text`, `path`, `size_bytes`, `truncated` |
| `file_list` | `_execute_list_dir()` | Yes | `text` (names), `entries` (list of dicts), `path`, `count` |
| `file_stat` | `_execute_stat_file()` | Yes | `path`, `exists`, `is_file`, `is_dir`, `size_bytes`, `modified_at`, `created_at` |

### Blocked (returns NOT_IMPLEMENTED)

| Operation | Status |
|-----------|--------|
| `file_write` | REJECTED — "Write operations not yet implemented" |
| `file_delete` | REJECTED — "Write operations not yet implemented" |

### Sandbox enforcement

All file operations pass through `check_file_operation()` which enforces:
- Path must resolve under `/opt/OS/data`, `/opt/OS/logs`, `/opt/OS/10_Wiki`, or `/tmp`
- Sensitive patterns blocked: `.env`, `credentials`, `secret`, `.ssh`, `.gnupg`, `private_key`
- Symlinks resolved with `os.path.realpath()` — no escape via symlink

### file_read limits

- Default max: 1MB (`max_bytes` in inputs, default 1,000,000)
- Encoding: UTF-8 with replacement characters for binary content
- Returns `truncated: True` if file exceeds max_bytes

---

## 5. Observability

### ExecutionEvent (structured record)

Every execution through `execute()` now produces a frozen `ExecutionEvent` with:

| Field | Source |
|-------|--------|
| `execution_id` | From request |
| `operation` | From request |
| `capability_type` | Classified by `_classify_capability()` — `llm_call`, `shell_command`, `file_operation`, `browser_action`, `os_interaction` |
| `execution_class` | From request (pure, side_effect, transport, llm_call) |
| `status` | From result (succeeded, failed, timed_out, rejected) |
| `latency_ms` | From result |
| `model_used` | From result (LLM only) |
| `cost_usd` | From result (LLM only) |
| `error` | From result (on failure/rejection) |
| `issued_by` | From request |
| `adapter` | Default: "spine" |

### EnhancedExecutionObserver

Replaces `LoggingExecutionObserver`. Produces:

```
[ExecutionObserver] request: id=exec_abc op=file_read class=side_effect capability=file_operation issued_by=test
[ExecutionObserver] result: id=exec_abc op=file_read capability=file_operation status=succeeded model=none latency=3ms cost=$0.000000
```

Two structured log lines per execution — same count as before, but with `capability_type` added to both.

### Observer factory change

```python
# Before (Phase 2B)
get_execution_observer_adapter() → LoggingExecutionObserver

# After (Phase 2C)
get_execution_observer_adapter() → EnhancedExecutionObserver
```

`LoggingExecutionObserver` class preserved in file as fallback reference.

---

## 6. Capability Scoring

### CapabilityScorer

Thread-safe, in-memory singleton at `umh/execution/scoring.py`.

| Method | Purpose |
|--------|---------|
| `record(event)` | Feed an ExecutionEvent — increments counters |
| `get_stats(capability_type)` | Returns `CapabilityStats` for one type |
| `get_all_stats()` | Returns dict of all types → stats dicts |
| `reset()` | Clear all accumulated stats |

### CapabilityStats fields

| Field | Type | Description |
|-------|------|-------------|
| `total_calls` | int | Total executions of this capability |
| `successful_calls` | int | Executions with status=succeeded |
| `failed_calls` | int | Executions with status=failed/timed_out |
| `rejected_calls` | int | Executions with status=rejected |
| `success_rate` | float | successful_calls / total_calls |
| `avg_latency_ms` | float | total_latency_ms / total_calls |
| `total_cost_usd` | float | Cumulative cost (LLM only) |
| `last_error` | str | Most recent error message |

### Integration

```
execute(request)
  → EnhancedExecutionObserver.on_request()    # stores pending request
  → backend.execute()
  → EnhancedExecutionObserver.on_result()     # builds ExecutionEvent
    → CapabilityScorer.record(event)          # updates per-capability stats
```

### Persistence

Not persisted — resets on process restart. Designed for operational visibility during a session, not billing or long-term analytics. Can be upgraded to Neon-backed persistence in a future phase.

---

## 7. Duplicate Cleanup

### Deleted (2 files)

| File | Size | Importers | Canonical copy |
|------|------|-----------|----------------|
| `umh/policy/regime_engine.py` | Byte-identical | 0 | `umh/runtime_engine/regime_engine.py` (5 importers) |
| `umh/policy/risk_model.py` | Byte-identical | 0 | `umh/runtime_engine/risk_model.py` (5 importers) |

### Why only 2 (not 6)?

The Phase 2A-Lite audit identified 6 orphans. Re-verification before deletion revealed that 4 of the 6 "RE orphans" now have test importers (tests import `umh.runtime_engine.X` while production code imports `umh.{modular_dir}.X`). Deleting them would break tests. Only the 2 `policy/` orphans remained truly importerless.

### Remaining duplicate landscape

| Category | Count | Status |
|----------|-------|--------|
| Orphan identical (deletable) | 0 | All cleared |
| Identical with importers | 13 pairs | Need import migration before deletion |
| Diverged minor | 16 pairs | Need import migration + code reconciliation |
| Diverged significant | 2 pairs | Keep both (wrapper/base pattern) |
| Not duplicate | 7 pairs | Same filename, different module |

---

## 8. Production Path Count — Final State

### Through execute() — all capabilities

| Capability | Operations | Status |
|------------|-----------|--------|
| LLM_CALL | 25 call sites across 13 modules | ACTIVE |
| SHELL_COMMAND | 12 allowlisted commands | ACTIVE |
| FILE_OPERATION (read) | file_read, file_list, file_stat | ACTIVE |
| FILE_OPERATION (write) | file_write, file_delete | STUB (NOT_IMPLEMENTED) |
| BROWSER_ACTION | browser_* | STUB (NOT_IMPLEMENTED) |
| OS_INTERACTION | os_* | STUB (NOT_IMPLEMENTED) |

### Security enforcement

| Layer | Scope | What it blocks |
|-------|-------|---------------|
| Engine guard | All SIDE_EFFECT/TRANSPORT | Metacharacters, out-of-sandbox, sensitive files |
| Backend allowlist | Shell commands | Non-allowlisted commands |
| Backend file guard | File operations | Redundant sandbox check (defense-in-depth) |

---

## 9. Test Coverage Summary

| Test file | Tests | Phase |
|-----------|-------|-------|
| `test_execution_capabilities.py` | 30 | Phase 2B (updated 2C) |
| `test_phase2c.py` | 31 | Phase 2C |
| **Phase 2B+2C total** | **61** | |
| **Full suite** | **773** | |

### Phase 2C test breakdown

| Class | Tests | Coverage |
|-------|-------|----------|
| TestSecurityGuardIntegration | 7 | Guard blocks metacharacters, sandbox escapes, sensitive files at engine level; allows safe commands; bypasses PURE/LLM |
| TestFileOperations | 10 | file_read (in/out sandbox, sensitive, nonexistent, truncation), file_list (in/out), file_stat (real/nonexistent), file_write blocked |
| TestCapabilityScoring | 8 | Success/failure/rejection recording, multi-call aggregation, get_all_stats, reset, cost accumulation, unknown type |
| TestObservability | 5 | ExecutionEvent creation, defaults, scorer integration, _classify_capability mapping |

---

## 10. Cumulative Impact (Phase 0 → 2C)

| Phase | What changed | Test count |
|-------|-------------|-----------|
| Phase 0 | 4 CRITICAL security fixes | 712 |
| Phase 1A | SpineExecutionBackend created | 712 |
| Phase 1B | 7 bypasses redirected + LoggingObserver | 712 |
| Phase 2A-Lite | 5 bypasses + max_tokens + substrate stubs | 712 |
| Phase 2B | Shell execution + security guard + capability spec | 741 |
| Phase 2C | Guard in hot path + file ops + scoring + observability | 773 |

**From NullExecutionBackend to security-enforced multi-capability engine with operational visibility.**
**773/773 tests pass across all phases. Zero regressions.**

---

## 11. Is Phase 2D Safe?

**YES.** Recommended Phase 2D scope:

1. **Apply max_tokens values** at call sites — email_gps=50, decision_log=150, quality_gate=500 (parameter threaded since Phase 2A-Lite, not yet used)
2. **Duplicate reconciliation** — Phase 2 of the reconciliation map: delete identical copies with 1-2 importers to fix (8 files, 9 import changes)
3. **Execution cost dashboard** — aggregate CapabilityScorer data into a queryable summary (daily cost, latency percentiles, failure rates)
4. **File write activation** — implement `file_write` for sandbox paths with size limits and backup-before-write

Phase 2D should NOT:
- Activate browser or OS operations
- Modify the shell allowlist
- Change the guard or engine architecture
- Touch sanctioned LLM bypasses
