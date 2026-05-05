# Phase 3A: Environment Abstraction Layer — Completion Report

**Date:** 2026-04-26
**Status:** COMPLETE
**Tests:** 800/800 unit tests pass (773 existing + 27 new), all files compile clean
**Approach:** Direct implementation (no parallel agents — tight dependencies between modules)

---

## 1. Executive Summary

Phase 3A introduced environment-aware execution routing without modifying
any existing capability behavior. Every execution is now classified with an
environment (currently always `local`) that describes where it runs, what
capabilities it supports, and its security posture. The environment is
captured in the observer, attached to structured events, and visible in logs.

**Zero behavior changes. Pure metadata addition. Extension point for
future container, sandbox, and remote execution.**

---

## 2. Files Created

| # | File | Purpose | Lines |
|---|------|---------|-------|
| 1 | `umh/execution/environment.py` | EnvironmentType enum, SecurityLevel enum, EnvironmentSpec dataclass, select_environment(), get_environment(), list_environments() | 86 |
| 2 | `tests/unit/test_phase3a.py` | 27 tests across 6 test classes | ~340 |

## 3. Files Modified

| # | File | Change |
|---|------|--------|
| 1 | `umh/execution/observability.py` | Added `environment_id` and `environment_type` fields to ExecutionEvent. Observer now calls `select_environment()` on request and attaches env to pending state and emitted events. Log lines include `env=` field. |

**Total: 2 files created, 1 file modified.**

---

## 4. Environment Type System

### EnvironmentType enum

| Value | Description | Current status |
|-------|-------------|---------------|
| `local` | Direct execution on host process | **ACTIVE** — all execution |
| `sandbox` | Restricted local environment | Future — for untrusted file ops |
| `container` | Docker/OCI container | Future — for shell commands |
| `remote` | Remote node via transport | Future — for distributed execution |

### SecurityLevel enum

| Value | Description | Trust model |
|-------|-------------|------------|
| `trusted` | Full host access | Local environment |
| `sandboxed` | Restricted access, limited blast radius | Sandbox environment |
| `isolated` | No host access, network-isolated | Container/remote environment |

### EnvironmentSpec dataclass

```python
@dataclass(frozen=True)
class EnvironmentSpec:
    id: str                                    # "local", "docker_sandbox", etc.
    env_type: EnvironmentType                  # LOCAL, SANDBOX, CONTAINER, REMOTE
    supported_capabilities: frozenset[str]     # {"llm_call", "shell_command", ...}
    security_level: SecurityLevel              # TRUSTED, SANDBOXED, ISOLATED
    metadata: dict[str, Any]                   # {"docker_image": "python:3.12", ...}

    def supports(capability_type: str) -> bool
```

---

## 5. Environment Selection

### Current routing (Phase 3A)

```
select_environment(request) → _LOCAL_ENV (always)
```

Every request type routes to the local environment. This is intentional —
Phase 3A establishes the abstraction; future phases add conditional routing.

### Local environment definition

```python
_LOCAL_ENV = EnvironmentSpec(
    id="local",
    env_type=EnvironmentType.LOCAL,
    supported_capabilities=frozenset({"llm_call", "shell_command", "file_operation"}),
    security_level=SecurityLevel.TRUSTED,
)
```

### Future routing (Phase 3B+)

```python
def select_environment(request):
    capability = _classify_capability(request)
    if capability == "shell_command" and request.constraints.sandbox:
        return _CONTAINER_ENV
    if capability == "file_operation" and is_untrusted(request):
        return _SANDBOX_ENV
    return _LOCAL_ENV
```

---

## 6. Execution Pipeline — Updated Flow

```
execute(request)
  → observer.on_request(request)
      → select_environment(request)           ← NEW
      → store (request, timestamp, env_id, env_type) in pending
      → log: env=local
  → security guard check (SIDE_EFFECT/TRANSPORT only)
  → backend.execute(request)
  → observer.on_result(result)
      → build ExecutionEvent with environment_id, environment_type  ← NEW
      → log: env=local
      → scorer.record(event)
```

### Log format (before and after)

**Before (Phase 2C):**
```
[ExecutionObserver] request: id=X op=shell_command class=side_effect capability=shell_command issued_by=test
[ExecutionObserver] result: id=X op=shell_command capability=shell_command status=succeeded model=none latency=3ms cost=$0.000000
```

**After (Phase 3A):**
```
[ExecutionObserver] request: id=X op=shell_command class=side_effect capability=shell_command env=local issued_by=test
[ExecutionObserver] result: id=X op=shell_command capability=shell_command status=succeeded env=local model=none latency=3ms cost=$0.000000
```

One field added to each log line. No format breaking changes.

---

## 7. ExecutionEvent — Updated Fields

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
| **environment_id** | **str** | **3A** |
| **environment_type** | **str** | **3A** |

Both fields default to `"local"` for backwards compatibility.

---

## 8. Test Coverage

### 27 new tests across 6 classes

| Class | Tests | Coverage |
|-------|-------|----------|
| TestEnvironmentSpec | 6 | Type values, creation, frozen immutability, supports(), metadata |
| TestEnvironmentSelector | 6 | LLM→local, shell→local, file→local, pure→local, transport→local, supported capabilities |
| TestEnvironmentRegistry | 3 | get by ID, get nonexistent, list all |
| TestExecutionEventEnvironment | 4 | Has fields, defaults to local, to_dict includes env, custom env values |
| TestObserverEnvironmentIntegration | 3 | Captures env on request, attaches to event, defaults without request |
| TestExecutionBehaviorUnchanged | 5 | Shell works, file_read works, guard blocks, LLM path works, not_implemented unchanged |

---

## 9. What Phase 3A Did NOT Change

- Execution behavior — identical to Phase 2C
- Security guard — untouched
- Backend routing — untouched
- Capability scoring — untouched (events now carry env but scorer doesn't use it yet)
- Shell allowlist — untouched
- File sandbox — untouched
- SANCTIONED LLM bypasses — untouched

---

## 10. Cumulative Impact (Phase 0 → 3A)

| Phase | What changed | Test count |
|-------|-------------|-----------|
| Phase 0 | 4 CRITICAL security fixes | 712 |
| Phase 1A | SpineExecutionBackend created | 712 |
| Phase 1B | 7 bypasses redirected + LoggingObserver | 712 |
| Phase 2A-Lite | 5 bypasses + max_tokens + substrate stubs | 712 |
| Phase 2B | Shell execution + security guard + capability spec | 741 |
| Phase 2C | Guard in hot path + file ops + scoring + observability | 773 |
| Phase 3A | Environment abstraction layer | 800 |

**800/800 tests pass across all phases. Zero regressions.**

---

## 11. Environment Mapping Summary

| ExecutionClass | Capability | Environment | Future target |
|----------------|-----------|-------------|---------------|
| LLM_CALL | llm_call | local (trusted) | local (always — LLM SDKs run in-process) |
| SIDE_EFFECT | shell_command | local (trusted) | container (isolated) when sandbox=True |
| SIDE_EFFECT | file_read | local (trusted) | sandbox (sandboxed) for untrusted sources |
| SIDE_EFFECT | file_list | local (trusted) | sandbox (sandboxed) for untrusted sources |
| SIDE_EFFECT | file_stat | local (trusted) | sandbox (sandboxed) for untrusted sources |
| SIDE_EFFECT | file_write | NOT_IMPLEMENTED | sandbox (sandboxed) when activated |
| SIDE_EFFECT | browser_* | NOT_IMPLEMENTED | container (isolated) |
| PURE | * | local (trusted) | local (always — no side effects) |
| TRANSPORT | * | local (trusted) | remote (when distributed) |

---

## 12. Is Phase 3B Safe?

**YES.** Recommended Phase 3B scope:

1. **Environment-aware scoring** — extend CapabilityScorer to track per-environment stats (local vs. container success rates)
2. **Sandbox environment definition** — add a `sandbox` EnvironmentSpec with restricted capabilities and `SecurityLevel.SANDBOXED`
3. **Conditional routing** — update `select_environment()` to route `shell_command` requests with `constraints.sandbox=True` to sandbox environment
4. **max_tokens deployment** — apply specific max_tokens values at call sites (email_gps=50, decision_log=150, quality_gate=500)

Phase 3B should NOT:
- Implement container or remote execution (no Docker runtime integration)
- Modify the security guard or backend
- Change existing capability behavior
- Touch sanctioned LLM bypasses
