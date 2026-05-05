# Phase 3B: Environment Activation (Scoring + Sandbox Routing) — Completion Report

**Date:** 2026-04-26
**Status:** COMPLETE
**Tests:** 832/832 unit tests pass (800 existing + 32 new), all files compile clean
**Approach:** Sequential (tight dependencies between environment → scoring → observer → tests)

---

## 1. Executive Summary

Phase 3B activated the environment abstraction introduced in Phase 3A. File
operations with `sandbox=True` constraints now route to a dedicated sandbox
environment. The capability scorer tracks per-environment statistics alongside
aggregate stats. The observer pipeline feeds environment_type through to the
scorer without any changes to observability.py — the existing event fields
were already sufficient.

**The system now differentiates execution environments in routing AND scoring,
without changing any execution behavior.**

---

## 2. Files Created

| # | File | Purpose | Lines |
|---|------|---------|-------|
| 1 | `tests/unit/test_phase3b.py` | 32 tests across 5 test classes | ~320 |

## 3. Files Modified

| # | File | Change |
|---|------|--------|
| 1 | `umh/execution/environment.py` | Added `_SANDBOX_ENV` EnvironmentSpec, registered in `_ENVIRONMENTS`, added `_FILE_OPERATIONS` frozenset, updated `select_environment()` to route sandboxed file ops to sandbox env |
| 2 | `umh/execution/scoring.py` | Added `_env_stats` dict with `(capability_type, environment_type)` composite keys, extracted `_record_into()` helper, added `get_env_stats()` and `get_all_env_stats()` methods, updated `reset()` to clear both dicts |

**Total: 1 file created, 2 files modified.**

---

## 4. Sandbox Environment Definition

```python
_SANDBOX_ENV = EnvironmentSpec(
    id="sandbox",
    env_type=EnvironmentType.SANDBOX,
    supported_capabilities=frozenset({"file_operation", "shell_command"}),
    security_level=SecurityLevel.SANDBOXED,
)
```

| Property | Value | Rationale |
|----------|-------|-----------|
| `id` | `"sandbox"` | Distinct from `"local"` for scoring separation |
| `env_type` | `SANDBOX` | Restricted local environment |
| `supported_capabilities` | `file_operation`, `shell_command` | No LLM calls in sandbox |
| `security_level` | `SANDBOXED` | Reduced blast radius vs. `TRUSTED` |

---

## 5. Conditional Routing

### select_environment() routing table

| Request operation | sandbox=False | sandbox=True |
|-------------------|---------------|--------------|
| `file_read` | local | **sandbox** |
| `file_list` | local | **sandbox** |
| `file_stat` | local | **sandbox** |
| `file_write` | local | **sandbox** |
| `file_delete` | local | **sandbox** |
| `shell_command` | local | local |
| `utility` (LLM) | local | local |
| `compute` (PURE) | local | local |
| any other | local | local |

Only file operations with `constraints.sandbox=True` route to sandbox.
All other operations stay local regardless of the sandbox flag.

---

## 6. Environment-Aware Scoring

### Dual-key architecture

```
record(event)
  → _stats[capability_type]                    # aggregate (backward-compatible)
  → _env_stats[(capability_type, env_type)]    # per-environment (new)
```

### API surface

| Method | Return | Scope |
|--------|--------|-------|
| `get_stats(cap_type)` | `CapabilityStats` | All environments combined |
| `get_env_stats(cap_type, env_type)` | `CapabilityStats` | Single environment |
| `get_all_stats()` | `dict[str, dict]` | All capabilities, aggregated |
| `get_all_env_stats()` | `dict[str, dict]` | All capability:environment pairs |

### Key format for get_all_env_stats()

```python
{"llm_call:local": {...}, "file_operation:sandbox": {...}}
```

### Invariant

For any capability type, the aggregate stats equal the sum of all
per-environment stats:

```
get_stats("file_operation").total_calls ==
    sum(get_env_stats("file_operation", env).total_calls for env in all_envs)
```

### Backward compatibility

`get_stats()` and `get_all_stats()` return identical data to Phase 3A.
No existing callers need modification.

---

## 7. Observer Pipeline (Unchanged)

The observer already:
1. Calls `select_environment(request)` on each request (Phase 3A)
2. Stores `(env_id, env_type)` in pending state (Phase 3A)
3. Attaches `environment_type` to `ExecutionEvent` (Phase 3A)
4. Passes event to `scorer.record()` (Phase 2C)

Phase 3B required **zero changes to observability.py**. The scorer now
reads `event.environment_type` (which was always present) and uses it
for the composite key. This is the benefit of the Phase 3A "additive
metadata" approach — the data was flowing through the pipeline before
the consumer was ready for it.

---

## 8. Test Coverage

### 32 new tests across 5 classes

| Class | Tests | Coverage |
|-------|-------|----------|
| TestSandboxEnvironmentDefinition | 7 | Registry lookup, type, security level, capability support (file_operation, shell_command, not llm_call), registry lists both envs |
| TestConditionalRouting | 9 | file_read/list/stat/write/delete with sandbox → sandbox; shell/llm/pure with sandbox → local; file_read without sandbox → local |
| TestEnvironmentAwareScoring | 8 | env_stats populated, separate by environment, aggregate unchanged, empty default, key format, reset clears both, failure tracking, cost accumulation |
| TestObserverEnvironmentPipeline | 3 | Sandboxed file → observer captures sandbox env; non-sandboxed → local; shell with sandbox → local |
| TestExecutionBehaviorUnchanged3B | 5 | Shell works, file_read works, guard blocks, sandbox flag doesn't change behavior, LLM path unchanged |

---

## 9. What Phase 3B Did NOT Change

- Execution behavior — file ops, shell, LLM all produce identical results
- Security guard — untouched
- Backend routing — untouched
- Observability module — untouched (zero changes to observability.py)
- Shell allowlist — untouched
- File sandbox enforcement — untouched
- SANCTIONED LLM bypasses — untouched

---

## 10. Cumulative Impact (Phase 0 → 3B)

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

**832/832 tests pass across all phases. Zero regressions.**

---

## 11. Is Phase 3C Safe?

**YES.** Recommended Phase 3C scope:

1. **Logging verification** — structured log queries confirming `env=sandbox` appears for sandboxed file operations in production
2. **Environment metrics dashboard** — surface `get_all_env_stats()` data through a queryable endpoint or CLI command
3. **max_tokens deployment** — apply specific max_tokens values at call sites (email_gps=50, decision_log=150, quality_gate=500)
4. **Container environment stub** — define `_CONTAINER_ENV` EnvironmentSpec for future shell command isolation

Phase 3C should NOT:
- Implement actual container/sandbox execution runtimes
- Modify the security guard or backend
- Change existing capability behavior
- Touch sanctioned LLM bypasses
