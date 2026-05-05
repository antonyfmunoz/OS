# Phase 5D: Event-Driven Orchestration Layer — Audit Report

**Date:** 2026-04-26
**Status:** COMPLETE

## Files Changed

| File | Action |
|------|--------|
| `umh/orchestrator/__init__.py` | NEW — package marker |
| `umh/orchestrator/engine.py` | NEW — Rule, Orchestrator, built-in rules, replay action |
| `umh/execution/engine.py` | Modified — stores pending requests for orchestrator replay |
| `umh/execution/approval.py` | Modified — moved event publishes outside locks (deadlock fix) |
| `umh/control/api.py` | Modified — added GET /orchestrator/rules endpoint |
| `tests/unit/test_phase5d.py` | NEW — 37 tests |

## Architecture

```
                    EventStream
                        │
                   subscribe()
                        │
                        ▼
                  ┌──────────────┐
                  │ Orchestrator │
                  │              │
                  │  Rules:      │
                  │  ┌─────────────────────────────────────────┐
                  │  │ approval.approved → replay execution    │
                  │  │ execution.completed → log pending       │
                  │  └─────────────────────────────────────────┘
                  │              │
                  │  Pending:    │
                  │  {exec_id → original_request}              │
                  │              │
                  │  Safety:     │
                  │  {approval_id → replay_count}              │
                  │  max_replays = 1                           │
                  └──────┬───────┘
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
    orchestration.  orchestration.  execute()
    triggered       executed        (replay)
```

## Flow: Approval Auto-Replay

```
1. execute(request)
   → guard says REQUIRES_APPROVAL
   → engine creates approval
   → engine stores request in orchestrator._pending_requests
   → engine emits execution.completed (requires_approval=True)

2. operator approves (API or CLI)
   → approval.approve() updates status
   → emits approval.approved event (OUTSIDE lock — critical)

3. EventStream calls orchestrator.handle_event(approval.approved)
   → matches builtin:replay_on_approval rule
   → condition: always true
   → action:
     a. check can_replay(approval_id) — max 1
     b. retrieve original request from pending store
     c. record_replay(approval_id)
     d. build new ExecutionRequest with approval_id in inputs
     e. emit orchestration.executed event
     f. call execute(replayed_request)
     g. remove pending request

4. execute(replayed_request)
   → validates approval_id → APPROVED
   → guard allows (approved_execution=True)
   → backend executes
   → consume(approval_id)
   → returns SUCCEEDED
```

## Rule Model

```python
@dataclass
class Rule:
    id: str                              # unique identifier
    event_type: str                      # event type to match
    condition: Callable[[Event], bool]   # predicate
    action: Callable[[Event], None]      # side-effecting handler
    description: str = ""                # human-readable
```

## Built-in Rules

| Rule ID | Event Type | Condition | Action |
|---------|-----------|-----------|--------|
| `builtin:replay_on_approval` | `approval.approved` | Always true | Replay original execution with approval_id |
| `builtin:log_pending_approval` | `execution.completed` | status=rejected AND requires_approval=True | Log pending approval |

## Safety Mechanisms

1. **Max replay = 1**: Each approval_id can trigger at most 1 replay. Tracked via `_replay_count` dict.
2. **Orchestration events ignored**: Events with type `orchestration.*` are never processed by rules, preventing self-triggering loops.
3. **Deduplication**: Each event ID is tracked in `_processed` set — same event never handled twice.
4. **Action errors caught**: Rule action exceptions are logged but never propagate.
5. **Condition errors caught**: Rule condition exceptions skip the rule silently.

## Critical Fix: Deadlock Prevention

The approval store previously published events INSIDE its `self._lock`. When the orchestrator's subscriber was called, it would call `execute()`, which calls `get_approval_store().validate_for_execution()`, which tries to acquire the same lock — causing a deadlock on the same thread (Python's `threading.Lock` is not reentrant).

**Fix**: All `_publish_event()` calls in `ApprovalStore.approve()`, `deny()`, and `consume()` were moved OUTSIDE the `with self._lock:` block. The lock protects the state mutation; the event publish happens after the lock is released.

## New Events

| Type | Source |
|------|--------|
| `orchestration.triggered` | Orchestrator, when a rule matches |
| `orchestration.executed` | Orchestrator, when replay executes |

## Pending Request Store

The engine stores the original `ExecutionRequest.to_dict()` in the orchestrator when a REQUIRES_APPROVAL result is generated. The orchestrator uses `ExecutionRequest.from_dict()` to reconstruct the request for replay.

- Stored keyed by `execution_id`
- Retrieved by the replay action using `approval.execution_id`
- Removed after successful replay
- In-memory only (lost on restart — acceptable for Phase 5D)

## API Extension

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/orchestrator/rules` | admin | List registered orchestration rules |

## Backwards Compatibility

- No ExecutionRequest/ExecutionResult schema changes
- No guard logic changes
- Approval store public API unchanged
- Event publish moved outside lock but behavior identical
- All Phase 4D/4E/4F/5A/5B/5C tests pass: 252 tests across phases

## Test Results

```
Phase 5D: 37 passed in 1.47s
Cross-phase (4D–5D): 252 passed in 87.72s
```

Test coverage:
- A. Rule core (2 tests): creation, to_dict
- B. Orchestrator core (10 tests): register, handle, matching, conditions, dedup, orchestration events ignored, errors, ordering, reset
- C. Pending request store (3 tests): store/retrieve, missing, remove
- D. Replay safety (3 tests): initial can_replay, limit enforced, independent approvals
- E. Built-in rules (3 tests): rules registered, replay matches approval.approved, pending matches rejected+requires_approval
- F. Orchestration events (1 test): orchestration.triggered emitted
- G. Event stream integration (2 tests): subscriber fires, publish triggers orchestrator
- H. Thread safety (1 test): 100 concurrent events across 4 threads
- I. End-to-end approval auto-replay (5 tests): full path, replay produces events, no double replay, cleanup, event ordering
- J. API (4 tests): auth, admin scope, returns rules, descriptions present
- K. Singleton (3 tests): same instance, reset creates new, start idempotent

## Validation

```bash
python3 -c "from umh.orchestrator.engine import Orchestrator, start_orchestrator; print('OK')"  # OK
python3 -c "from umh.execution.engine import execute; print('OK')"                               # OK
python3 -c "from umh.control.api import app; print('OK')"                                        # OK
```
