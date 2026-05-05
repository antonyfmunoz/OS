# Phase 5C: Event Stream + State Sync — Audit Report

**Date:** 2026-04-26
**Status:** COMPLETE

## Files Changed

| File | Action |
|------|--------|
| `umh/events/__init__.py` | NEW — package marker |
| `umh/events/stream.py` | NEW — Event dataclass, EventStream, global singleton, publish() |
| `umh/execution/engine.py` | Modified — emits execution.started and execution.completed events |
| `umh/execution/approval.py` | Modified — emits approval.created/approved/denied/consumed events |
| `umh/control/api.py` | Modified — added GET /events and GET /events/stream (SSE) endpoints |
| `tests/unit/test_phase5c.py` | NEW — 45 tests |
| `tests/unit/test_phase4f.py` | Fixed — flaky shutil.rmtree WAL race condition |

## Architecture

```
  Engine.execute()  ──→  publish("execution.started")
       │                         │
       ├── backend.execute()     │
       │                         ▼
       └──→ publish("execution.completed")
                                 │
  ApprovalStore                  │
    .create_approval() ─→ publish("approval.created")
    .approve()         ─→ publish("approval.approved")
    .deny()            ─→ publish("approval.denied")
    .consume()         ─→ publish("approval.consumed")
                                 │
                                 ▼
                          ┌─────────────┐
                          │ EventStream  │
                          │  (deque)     │
                          │  subscribers │
                          └──────┬──────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼             ▼
              GET /events   GET /events/   subscribe()
              (JSON list)   stream (SSE)   (callback)
```

## Event Model

```python
@dataclass(frozen=True)
class Event:
    id: str             # "evt_<12hex>"
    type: str           # "execution.started", "approval.created", etc.
    timestamp: str      # ISO 8601
    payload: dict       # type-specific data
    actor_id: str       # identity ID of the actor
    execution_id: str   # linked execution (if applicable)
    approval_id: str    # linked approval (if applicable)
```

## Event Types

| Type | Source | Payload |
|------|--------|---------|
| `execution.started` | engine.execute() | operation, execution_class |
| `execution.completed` | engine.execute() | operation, status, latency_ms |
| `approval.created` | ApprovalStore.create_approval() | operation, capability_type, risk_level |
| `approval.approved` | ApprovalStore.approve() | operation |
| `approval.denied` | ApprovalStore.deny() | operation |
| `approval.consumed` | ApprovalStore.consume() | operation |

## EventStream

- **Storage**: `deque(maxlen=10_000)` — bounded, auto-evicts oldest
- **Thread-safe**: `threading.Lock` + `threading.Condition` for all operations
- **Publish**: appends event, notifies all subscribers synchronously
- **Subscribe**: register callback; called on each publish
- **Unsubscribe**: remove callback; safe even if not registered
- **list_events(limit)**: returns last N events, preserving order
- **wait_for_event(timeout)**: blocks until new event or timeout (for SSE)
- **Subscriber errors**: caught and swallowed — never break publish

## API Endpoints

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/events` | metrics:read | List recent events (JSON array) |
| GET | `/events/stream` | metrics:read | SSE stream of real-time events |

### GET /events

Query parameters:
- `limit` (default 100, max 1000)

Returns JSON array of event objects, most recent last.

### GET /events/stream

Server-Sent Events endpoint. Pushes new events as `data:` frames.
Keepalive comments (`: keepalive`) sent every ~5 seconds.

```
data: {"id":"evt_abc123","type":"execution.started","timestamp":"...","payload":{...},"actor_id":"...","execution_id":"...","approval_id":""}

data: {"id":"evt_def456","type":"execution.completed","timestamp":"...","payload":{...},"actor_id":"...","execution_id":"...","approval_id":""}
```

## Integration Points

### Engine (execution.started + execution.completed)

- `execution.started` emitted at the top of `execute()`, before observer
- `execution.completed` emitted on ALL exit paths:
  - Normal completion (after backend.execute)
  - Approval-invalid rejection
  - Requires-approval rejection
  - Guard-denied rejection
- Both carry `actor_id=request.issued_by` and `execution_id`

### ApprovalStore (approval.*)

- Events emitted after the backend write succeeds (not before)
- `approval.created` includes the requesting actor_id
- `approval.approved` includes the approving actor_id
- `approval.denied` and `approval.consumed` have empty actor_id
  (could be enriched when deny/consume gain actor tracking)

## Safety Constraints

1. No ExecutionRequest/ExecutionResult schema changes
2. No guard architecture modifications
3. No external services (no Kafka, Redis, etc.)
4. Events are in-memory only (bounded deque, lost on restart)
5. Subscriber errors cannot break publish
6. Event dataclass is frozen (immutable after creation)
7. SSE endpoint respects existing scope enforcement

## Backwards Compatibility

- All existing API endpoints unchanged
- Engine behavior unchanged — events are side-effect-only
- ApprovalStore API unchanged — events are emitted after mutations
- All Phase 4D/4E/4F/5A/5B tests pass: 215 tests across phases
- Full suite: 1251 tests (pending confirmation)

## Test Results

```
Phase 5C: 45 passed in 59.36s
Cross-phase (4D+4E+4F+5A+5B+5C): 215 passed in 83.45s
```

Test coverage:
- A. Event core (4 tests): dataclass, to_dict, immutability, defaults
- B. EventStream (8 tests): publish/list, limit, subscribe, unsubscribe, error handling, bounded, clear, ordering
- C. Thread safety (4 tests): concurrent publish, concurrent subscribe+publish, wait_for_event, timeout
- D. Module-level publish (3 tests): creates event, adds to stream, full metadata
- E. Execution events (4 tests): started+completed emitted, metadata, status, ordering
- F. Approval events (6 tests): created, approved, denied, consumed, full lifecycle, approval_id
- G. Events API (6 tests): auth required, scope enforcement, returns events, limit, metrics scope, full metadata
- H. SSE endpoint (6 tests): auth required, scope enforcement, subscriber mechanism, execution events, approval events, JSON serialization
- I. Global singleton (2 tests): same instance, reset creates new
- J. Integration (2 tests): execute via API produces events, approval via API produces events

## Validation

```bash
python3 -c "from umh.events.stream import Event, EventStream, publish; print('OK')"  # OK
python3 -c "from umh.execution.engine import execute; print('OK')"                    # OK
python3 -c "from umh.control.api import app; print('OK')"                             # OK
```
