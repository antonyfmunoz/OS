# Phase 75B Recommended Plan — Control Plane + Governance + Execution Spine Scaffold

> Created: 2026-05-02 | Status: READY FOR REVIEW (not yet executed)

---

## Goal

Wire the MVP harness so that every external signal flows through:
```
Gateway → Control Plane → Run Loop → Governance → Execution Engine → Adapter → Memory → Trace
```

No new intelligence features. No new adapters. Pure wiring and consolidation.

---

## Proposed File Structure

### New files to create

```
umh/control/middleware.py      — request validation, rate limiting stub
umh/control/trace_store.py     — persist and query RunTrace records
umh/execution/backend_registry.py — auto-discover and register execution backends
umh/execution/governance_gate.py  — universal governance wrapper for all execution paths
```

### Files to modify (wiring only)

```
umh/control/api.py             — add /traces endpoint, wire identity persistence
umh/control/identity.py        — add Neon-backed persistence
umh/run.py                     — add optional intelligence enrichment hook (stage 4)
umh/execution/engine.py        — add backend auto-discovery on first call
umh/runtime_loop/action_executor.py — route through governance gate
umh/gateway/entry.py           — ensure all interface paths route here
```

### Files NOT to touch

```
umh/runtime/           — intelligence kernel is stable, don't modify
umh/runtime_engine/    — legacy layer, deprecation handled separately
umh/substrate/         — operator layer, wiring handled in Phase 76+
umh/interfaces/        — interface migration is Phase 76+
umh/protocols/         — contracts are stable
umh/world/             — world model is stable
```

---

## Interfaces / Protocols

### GovernanceGate (new)

```python
# umh/execution/governance_gate.py
from umh.governance.authority import AuthorityLevel, check_governance
from umh.execution.contract import ExecutionRequest, ExecutionResult

def governed_execute(
    request: ExecutionRequest,
    authority: AuthorityLevel = AuthorityLevel.ANALYZE,
) -> ExecutionResult:
    """Universal governance-wrapped execution.
    
    All execution paths should call this instead of execute() directly.
    This ensures governance is checked before every execution.
    """
    check = check_governance(request, authority)
    if not check.approved:
        return ExecutionResult(
            status="blocked",
            output=f"Governance blocked: {check.reason}",
            ...
        )
    return execute(request)
```

### TraceStore (new)

```python
# umh/control/trace_store.py
from umh.run import RunTrace

class TraceStore:
    """Persist and query RunTrace records."""
    
    def save(self, trace: RunTrace) -> None: ...
    def get(self, run_id: str) -> RunTrace | None: ...
    def list_recent(self, limit: int = 50) -> list[RunTrace]: ...
```

### BackendRegistry (new)

```python
# umh/execution/backend_registry.py
from umh.execution.interfaces import ExecutionBackend

def auto_discover_backend() -> ExecutionBackend:
    """Discover the best available execution backend.
    
    Priority: configured backend > LLM adapter > null adapter.
    """
    ...
```

---

## Minimal Classes

### Identity Persistence

Extend `umh.control.identity.IdentityStore` with a Neon-backed implementation:

```python
class NeonIdentityStore(IdentityStore):
    """Persists identities to Neon."""
    def save(self, identity: Identity) -> None: ...
    def load(self, identity_id: str) -> Identity | None: ...
```

### Intelligence Hook

Add to `umh.run.run()` stage 4 (decision):

```python
# Optional intelligence enrichment
if config.intelligence_enabled:
    from umh.runtime.advisor import get_advisor
    advisor = get_advisor()
    enrichment = advisor.get_decision_context(intent, world_context, goal)
    # Merge enrichment into decision context
```

---

## How Existing Runtime/Intelligence Kernel Plugs In

The intelligence kernel (`umh.runtime/`) operates as a pure advisory layer:

```
run.py stage 4 (decision)
  ↓
  if intelligence_enabled:
    ↓
    runtime.advisor.get_decision_context()
      → reads regime state (runtime.regime)
      → reads pattern signals (runtime.pattern_matching)
      → reads weight context (runtime.weighted_decision)
      → returns enrichment dict
    ↓
    merge into context_builder sections
  ↓
  continue to stage 5 (compose)
```

The kernel never executes. It only provides context that influences LLM prompts
and capability selection. Governance still gates all execution.

---

## What NOT to Touch in 75B

1. **Intelligence kernel** — stable, well-tested, bounded invariants
2. **Legacy runtime_engine** — deprecation is a separate track
3. **Substrate operator layer** — complex, operational, has its own tests
4. **Interfaces** — Discord/Telegram migration is Phase 76+
5. **Distributed runtime** (nodes, cells) — FUTURE classification
6. **Learning/prediction pipeline** — enhancement, not MVP

---

## Tests Needed

### Unit Tests

```
tests/unit/test_phase75b_governance_gate.py
  - governed_execute blocks insufficient authority
  - governed_execute passes sufficient authority
  - blocked execution creates approval record
  - governance decision appears in trace

tests/unit/test_phase75b_trace_store.py
  - save and retrieve trace by run_id
  - list_recent returns ordered traces
  - missing run_id returns None

tests/unit/test_phase75b_backend_registry.py
  - auto-discover finds LLM adapter
  - auto-discover falls back to null adapter
  - explicit backend takes priority

tests/unit/test_phase75b_identity_persistence.py
  - create identity persists to Neon
  - load identity from Neon
  - identity survives restart
```

### Integration Tests

```
tests/integration/test_phase75b_end_to_end.py
  - POST /run → full 9-stage loop → response with trace
  - POST /run with insufficient authority → governance block
  - GET /traces/{run_id} returns stored trace
  - POST /identity → GET /identity/{id} round-trip

tests/integration/test_phase75b_null_adapter.py
  - full run with null adapter (no external calls)
  - all 9 stages execute
  - outcome recorded in memory
```

---

## Acceptance Criteria

1. `POST /run {"input": "What should I focus on today?"}` returns 200 with RunResult
2. RunTrace contains timing for all 9 stages
3. Trace is persisted and retrievable via `GET /traces/{run_id}`
4. Governance blocks EXECUTE-class operations at ANALYZE authority
5. Identity is created, persisted, and used for authentication
6. Null adapter allows full loop without external dependencies
7. Intelligence kernel enrichment can be toggled on/off
8. All existing tests still pass (no regressions)
9. No new dependencies added to pyproject.toml
10. Zero new `subprocess` imports in clean packages

---

## Estimated Scope

| Component | New Files | Modified Files | Estimated Lines |
|-----------|----------|---------------|----------------|
| Governance gate | 1 | 0 | ~60 |
| Trace store | 1 | 1 | ~80 |
| Backend registry | 1 | 1 | ~50 |
| Identity persistence | 0 | 1 | ~40 |
| Intelligence hook | 0 | 1 | ~20 |
| Request validation | 1 | 1 | ~40 |
| Tests | 6 | 0 | ~400 |
| **Total** | **10** | **5** | **~690** |

This is a focused, low-risk phase that wires existing components without
building new features.
