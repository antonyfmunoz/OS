# Law 5.9 Adapter Classification — 2026-05-14

6 files in `execution/workers/workstation/` with `execute()` method.
Classified per §14.1 contract applicability.

## Classification

| File | Class | Classification | Rationale |
|------|-------|---------------|-----------|
| `governed_shell_adapter_v1.py` | GovernedShellAdapter | **ADAPTER** | Crosses OS boundary via subprocess.run(). Governance → subprocess → result normalization. |
| `governed_browser_adapter_v1.py` | GovernedBrowserAdapter | **ADAPTER** | Crosses browser/GUI boundary. Governance → browser action → result normalization. |
| `browser_execution_orchestrator_v1.py` | BrowserExecutionOrchestrator | **INTERNAL_WORKER** | Routes between browser + GUI adapters. Never crosses system boundary. |
| `workstation_execution_orchestrator_v1.py` | WorkstationExecutionOrchestrator | **INTERNAL_WORKER** | Routes between shell + tmux adapters. Never crosses system boundary. |
| `browser_gui_embodiment_engine_v1.py` | BrowserGUIEmbodimentEngine | **INTERNAL_WORKER** | Thin facade over BrowserExecutionOrchestrator. execute() = self._orchestrator.execute(). |
| `workstation_operational_embodiment_engine_v1.py` | WorkstationOperationalEmbodimentEngine | **INTERNAL_WORKER** | Thin facade over WorkstationExecutionOrchestrator. execute() = self._orchestrator.execute(). |

## Tally

| Classification | Count | Action |
|---------------|-------|--------|
| ADAPTER | 2 | Refactor to §14.1 |
| INTERNAL_WORKER | 4 | OUT_OF_SCOPE (per Law 5.4 precedent) |
| HYBRID | 0 | — |

## §14.1 Phase Boundaries (ADAPTER files)

### GovernedShellAdapter

| Phase | Current code | Method boundary |
|-------|-------------|-----------------|
| translate_request | `request.command` → stripped command string | Input is already typed (WorkstationExecutionRequest) |
| validate_operation | `evaluate_command()` — allowlist/block/chain checks | Already a separate method |
| do_work | `subprocess.run()` — the actual OS boundary crossing | Lines 242-250 |
| normalize_result | WorkstationExecutionResult construction from returncode/stdout/stderr | Lines 251-270 |
| observe_state | `get_decisions()`, `get_stats()` | Already exposed |

### GovernedBrowserAdapter

| Phase | Current code | Method boundary |
|-------|-------------|-----------------|
| translate_request | `request` → BrowserExecutionRequest (already typed) | Input is already canonical |
| validate_operation | `evaluate_action()` — domain/pattern/mode/scope checks | Already a separate method |
| do_work | `_execute_action()` — browser/GUI boundary crossing | Already a separate method |
| normalize_result | Result construction with duration + verdict | Lines 243-246 |
| observe_state | `get_decisions()`, `get_stats()` | Already exposed |

## Key Finding

Both adapters **already implement the spirit of §14.1** — they have:
- Governance as a separate callable method (evaluate_command / evaluate_action)
- Execution as a separate internal method (_execute_action / subprocess.run)
- State observation exposed (get_decisions / get_stats)

The refactor is mechanical: expose translate_request + normalize_result as
public methods, rename validate → validate_operation for contract compliance,
add observe_state returning StateSnapshot-compatible dict. execute() becomes
a thin orchestrator calling the 4 phases.

## INTERNAL_WORKER Deferral (per Law 5.4 precedent)

The 4 orchestrator/engine files are OUT_OF_SCOPE because:
1. They delegate to adapters — they don't cross system boundaries
2. Law 5.10 (Action/Execution Separation) explicitly distinguishes
   "Workers execute" from "Adapters translate"
3. The orchestrators' execute() is an internal coordination method,
   not a deprecated adapter contract
4. Same reasoning as Law 5.4 deferral: infrastructure-layer types
   serving a different purpose than the protocol contract

## External Callers

| File | External callers |
|------|-----------------|
| GovernedShellAdapter | tests only (WorkstationExecutionOrchestrator uses it internally) |
| GovernedBrowserAdapter | tests only (BrowserExecutionOrchestrator uses it internally) |
| Orchestrators | `execution/runtime/live_execution_coordinator_v1.py` + tests |
| Embodiment engines | tests only |

Refactoring the 2 adapters will not break callers — execute() is preserved
as backward-compatible orchestrator.
