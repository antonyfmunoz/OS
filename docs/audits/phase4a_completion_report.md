# Phase 4A: External Capability Interface Layer — Completion Report

**Date:** 2026-04-26
**Status:** COMPLETE
**Tests:** 919/919 unit tests pass (872 existing + 47 new), all files compile clean
**Approach:** Sequential (interface → adapters → routing → enforcement → tests)

---

## 1. Executive Summary

Phase 4A introduced external tools (browser, computer use) as first-class
capabilities routed through the existing execution pipeline. Every external
capability is classified, routed to an environment, enforcement-checked,
executed via a pluggable adapter, observed, and scored — exactly like
internal capabilities. No direct calls. No bypass paths.

Currently all external adapters return NOT_IMPLEMENTED. The infrastructure
is wired end-to-end and ready for real implementations without any
architecture changes.

**External tools now follow the same execution contract as internal tools.**

---

## 2. Files Created

| # | File | Purpose | Lines |
|---|------|---------|-------|
| 1 | `umh/execution/external.py` | ExternalCapabilityAdapter ABC, adapter registry (register/get/list) | ~85 |
| 2 | `umh/adapters/browser_adapter.py` | BrowserAdapter stub — NOT_IMPLEMENTED for all browser_* ops | ~35 |
| 3 | `umh/adapters/computer_use_adapter.py` | ComputerUseAdapter stub — NOT_IMPLEMENTED for all computer_* ops | ~35 |
| 4 | `tests/unit/test_phase4a.py` | 47 tests across 10 test classes | ~370 |

## 3. Files Modified

| # | File | Change |
|---|------|--------|
| 1 | `umh/capabilities/spec.py` | Added `COMPUTER_USE = "computer_use"` to CapabilityType enum |
| 2 | `umh/execution/environment.py` | Added `computer_` prefix classification. Added `computer_use` to local env capabilities. Added `_CONTAINER_ENV` (isolated, supports browser_action + shell_command). Registered container in `_ENVIRONMENTS`. |
| 3 | `umh/execution/observability.py` | Added `computer_` prefix classification to `_classify_capability()` |
| 4 | `umh/adapters/umh_execution.py` | Updated `can_handle()` for browser/computer/os prefixes. Replaced inline browser stub with `_execute_external()` routing to adapter registry. Added `_classify_external()`. Added `_register_external_adapters()` called from backend factory. |
| 5 | `tests/unit/test_phase3b.py` | Changed `len(envs) == 2` to `len(envs) >= 2` (3 envs now) |

**Total: 4 files created, 5 files modified.**

---

## 4. Capability Type System

### CapabilityType enum (updated)

| Value | Status | Environment | Adapter |
|-------|--------|-------------|---------|
| `llm_call` | ACTIVE | local | built-in (_execute_llm) |
| `shell_command` | ACTIVE | local / sandbox | built-in (_execute_shell) |
| `file_operation` | ACTIVE | local / sandbox | built-in (_execute_file_*) |
| `browser_action` | **STUB** | **container** | **browser_adapter** |
| `computer_use` | **STUB** | **local** | **computer_use_adapter** |
| `os_interaction` | STUB | — | — (no adapter yet) |

### Classification rules

| Operation prefix | Capability type |
|-----------------|-----------------|
| LLM_CALL class | `llm_call` |
| `shell_command` | `shell_command` |
| `file_read/list/stat/write/delete` | `file_operation` |
| `browser_*` | `browser_action` |
| `computer_*` | `computer_use` |
| `os_*` | `os_interaction` |

Both `_classify_capability()` functions (environment.py and observability.py)
are kept in sync and verified by test.

---

## 5. External Capability Interface

### ExternalCapabilityAdapter (ABC)

```python
class ExternalCapabilityAdapter(ABC):
    adapter_name: str       # "browser_adapter", "computer_use_adapter"
    capability_type: str    # "browser_action", "computer_use"

    def execute(request, environment) → ExecutionResult
    def _not_implemented(request, reason) → ExecutionResult  # built-in helper
```

### Adapter Registry

```python
register_adapter(adapter)            # register by capability_type
get_adapter(capability_type) → adapter | None
list_adapters() → {capability_type: adapter_name}
```

### Contract

Every adapter:
- Receives `ExecutionRequest` + `EnvironmentSpec`
- Returns `ExecutionResult` — never raises
- Cannot bypass enforcement (enforcement runs before adapter)
- Cannot bypass the security guard (guard runs before backend)
- Is observed and scored via the normal pipeline

---

## 6. Environment Mapping

### Three registered environments

| Environment | Type | Security | Supported capabilities |
|-------------|------|----------|----------------------|
| local | LOCAL | TRUSTED | llm_call, shell_command, file_operation, **computer_use** |
| sandbox | SANDBOX | SANDBOXED | file_operation, shell_command |
| **container** | **CONTAINER** | **ISOLATED** | **browser_action**, **shell_command** |

### Routing decisions

| Capability | sandbox=False | sandbox=True |
|-----------|---------------|--------------|
| llm_call | local | local |
| shell_command | local | local |
| file_operation | local | sandbox |
| **browser_action** | **container** | **container** |
| **computer_use** | **local** | **local** |

Browser always routes to container (only environment supporting it).
Computer use always routes to local (only environment supporting it).

---

## 7. Routing Architecture

### Execution flow for external capabilities

```
execute(request)
  │
  ├─ observer.on_request()
  │     └─ select_environment() → container (for browser)
  │     └─ enforce_environment() → ALLOW
  │
  ├─ security guard check (SIDE_EFFECT)
  │     └─ check_execution("browser_navigate", inputs)
  │     └─ → DENY: "Browser actions not yet implemented"
  │
  └─ [if guard allows in future]:
      backend.execute()
        └─ _execute_side_effect()
            └─ _execute_external()
                └─ _classify_external("browser_navigate") → "browser_action"
                └─ get_adapter("browser_action") → BrowserAdapter
                └─ adapter.execute(request, environment)
                    └─ → NOT_IMPLEMENTED
```

**Note:** Currently the security guard denies browser_* and os_* operations
before they reach the backend. This is correct — when real implementations
are added, the guard will be updated to allow specific operations.

### Backend routing (updated)

```
_execute_side_effect(request)
  ├─ shell_command → _execute_shell()
  ├─ file_read → _execute_file_read()
  ├─ file_list → _execute_list_dir()
  ├─ file_stat → _execute_stat_file()
  ├─ file_write/delete → _not_implemented()
  └─ anything else → _execute_external()    ← NEW
       ├─ adapter found → adapter.execute()
       └─ adapter not found → _not_implemented()
```

---

## 8. Stub Adapter Responses

### BrowserAdapter

```python
BrowserAdapter.execute(request, env)
  → ExecutionResult(
      status=REJECTED,
      outputs={
          "not_implemented": True,
          "reason": "Browser automation not yet implemented: browser_navigate",
          "adapter": "browser_adapter",
      },
      error="Browser automation not yet implemented: browser_navigate",
  )
```

### ComputerUseAdapter

```python
ComputerUseAdapter.execute(request, env)
  → ExecutionResult(
      status=REJECTED,
      outputs={
          "not_implemented": True,
          "reason": "Computer use not yet implemented: computer_screenshot",
          "adapter": "computer_use_adapter",
      },
      error="Computer use not yet implemented: computer_screenshot",
  )
```

Both include `adapter` in outputs for observability tracing.

---

## 9. Enforcement Compatibility

| Capability | Environment | Enforcement result |
|-----------|-------------|-------------------|
| browser_action | container | ALLOW |
| browser_action | local | **DENY** — local doesn't support browser_action |
| browser_action | sandbox | **DENY** — sandbox doesn't support browser_action |
| computer_use | local | ALLOW |
| computer_use | sandbox | **DENY** — sandbox doesn't support computer_use |
| computer_use | container | **DENY** — container doesn't support computer_use |

Enforcement runs BEFORE the adapter executes. An external capability
cannot bypass constraints — the same invariant as internal capabilities.

---

## 10. Test Coverage

### 47 new tests across 10 classes

| Class | Tests | Coverage |
|-------|-------|----------|
| TestCapabilityTypeEnum | 3 | COMPUTER_USE exists, BROWSER_ACTION exists, all 6 types present |
| TestCapabilityClassification | 6 | browser_navigate → browser_action, browser_click → browser_action, computer_screenshot → computer_use, computer_click → computer_use, observability matches environment classification, LLM unchanged |
| TestEnvironmentMapping | 8 | Container exists, type=CONTAINER, supports browser_action, not llm_call, security=ISOLATED, local supports computer_use, 3 envs registered, browser→container, computer→local |
| TestExternalCapabilityInterface | 4 | Interface callable, register+get, list_adapters, get nonexistent=None |
| TestBrowserAdapterStub | 4 | adapter_name, capability_type, execute→NOT_IMPLEMENTED+adapter field, error includes operation |
| TestComputerUseAdapterStub | 3 | adapter_name, capability_type, execute→NOT_IMPLEMENTED+adapter field |
| TestRoutingIntegration | 5 | Browser routes via factory adapter, computer_use routes via adapter, can_handle browser/computer, unknown→not_implemented |
| TestEnforcementCompatibility | 5 | Browser→container ALLOW, browser→local DENY, computer→local ALLOW, computer→sandbox DENY, LLM→sandbox DENY |
| TestObservabilityExternal | 4 | Browser event has correct capability_type+adapter, computer_use event correct, observer classifies browser, observer classifies computer |
| TestExistingBehaviorUnchanged | 5 | Shell works, file_read works, guard blocks, LLM unchanged, browser through execute gets guard |

### Updated prior phase tests

| File | Change |
|------|--------|
| `test_phase3b.py` | Changed `len(envs) == 2` to `len(envs) >= 2` |

---

## 11. What Phase 4A Did NOT Change

- No real browser automation implemented
- No MCP, OpenCLI, or Obscura integration
- No container/sandbox runtime (actual process isolation)
- Security guard logic untouched (still denies browser_*/os_*)
- ExecutionRequest schema untouched
- Existing capability behavior identical
- Shell allowlist untouched
- SANCTIONED LLM bypasses untouched

---

## 12. External Capability Architecture

```
                    ┌──────────────────┐
                    │ ExecutionRequest  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  execute()       │
                    │  ├─ observer     │
                    │  ├─ guard        │
                    │  └─ backend      │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───────┐ ┌───▼────┐ ┌───────▼────────┐
     │ _execute_llm() │ │ shell  │ │_execute_external│
     │   (built-in)   │ │ file_* │ │   (registry)    │
     └────────────────┘ └────────┘ └───────┬────────┘
                                           │
                              ┌────────────┼────────────┐
                              │            │            │
                     ┌────────▼───┐ ┌──────▼──────┐ ┌──▼──┐
                     │  Browser   │ │ ComputerUse │ │ ... │
                     │  Adapter   │ │  Adapter    │ │     │
                     └────────────┘ └─────────────┘ └─────┘
                              │            │
                     ┌────────▼───┐ ┌──────▼──────┐
                     │ container  │ │    local     │
                     │ (isolated) │ │  (trusted)   │
                     └────────────┘ └─────────────┘
```

### Adding a new external capability

1. Create adapter in `umh/adapters/` implementing `ExternalCapabilityAdapter`
2. Add classification rule in both `_classify_capability()` functions
3. Add capability to appropriate environment's `supported_capabilities`
4. Register adapter in `_register_external_adapters()`
5. Update guard if needed (currently blocks unknown ops)
6. Write tests

No changes needed to: engine, contract, observer, scorer, or enforcement.

---

## 13. Cumulative Impact (Phase 0 → 4A)

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

**919/919 tests pass across all phases. Zero regressions.**

---

## 14. Capability Routing Map (Full System)

| Capability | Operations | ExecutionClass | Environment | Adapter | Status |
|-----------|-----------|----------------|-------------|---------|--------|
| llm_call | 12 operation types | LLM_CALL | local | built-in | ACTIVE |
| shell_command | 12 allowlisted | SIDE_EFFECT | local | built-in | ACTIVE |
| file_operation | read/list/stat | SIDE_EFFECT | local/sandbox | built-in | ACTIVE |
| file_operation | write/delete | SIDE_EFFECT | local/sandbox | built-in | STUB |
| browser_action | navigate/click/type/screenshot/extract | SIDE_EFFECT | container | browser_adapter | STUB |
| computer_use | screenshot/click/type/scroll/key | SIDE_EFFECT | local | computer_use_adapter | STUB |
| os_interaction | * | SIDE_EFFECT | — | — | NOT WIRED |

---

## 15. Is Phase 4B Safe?

**YES.** Recommended Phase 4B scope:

1. **Computer use implementation** — integrate Anthropic Computer Use API via the adapter (local execution, no container needed)
2. **Guard update for computer_use** — allow computer_* operations through the security guard
3. **Browser adapter implementation** — integrate Playwright via container env when container runtime exists
4. **Execution metrics CLI** — `python3 -m umh.execution.metrics` to surface scoring data

Phase 4B should NOT:
- Implement container runtime (Docker integration)
- Add async or agent patterns
- Modify enforcement or the execution contract
- Change existing capability behavior
