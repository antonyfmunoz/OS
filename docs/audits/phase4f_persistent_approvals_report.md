# Phase 4F: Persistent Approval Store — Audit Report

**Date:** 2026-04-26
**Status:** COMPLETE

## Files Changed

| File | Action |
|------|--------|
| `umh/execution/approval.py` | Refactored to pluggable backend architecture |
| `umh/execution/approval_persistence.py` | NEW — backend protocol + InMemory + SQLite implementations |
| `tests/unit/test_phase4f.py` | NEW — 28 tests |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ApprovalStore                          │
│  (public API unchanged — same methods as before)         │
│                                                          │
│  Backend selection:                                       │
│    PYTEST_CURRENT_TEST set → InMemoryApprovalBackend     │
│    UMH_APPROVAL_BACKEND=memory → InMemoryApprovalBackend │
│    UMH_APPROVAL_BACKEND=test → InMemoryApprovalBackend   │
│    default → SQLiteApprovalBackend                        │
└────────────────────┬────────────────────────────────────┘
                     │ delegates to
          ┌──────────┴──────────┐
          ▼                     ▼
 InMemoryApprovalBackend   SQLiteApprovalBackend
 (dict, tests only)        (data/runtime/approvals.sqlite)
                            WAL mode, busy_timeout=3000ms
```

## Storage Schema

```sql
CREATE TABLE approvals (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    capability_type TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'high',
    inputs_summary TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    updated_at TEXT NOT NULL
);

CREATE TABLE approval_counters (
    name TEXT PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
);
```

## Cross-Process Behavior

Validated via actual subprocess invocation:
1. Process A creates approval → writes to SQLite
2. Process B (separate Python process) reads same SQLite file → sees approval
3. Process B approves it → writes APPROVED status
4. Process A (new store instance) validates → approval is valid

This eliminates the singleton-sharing limitation of the in-memory store.

## Backend Selection Logic

| Condition | Backend | Reason |
|-----------|---------|--------|
| `PYTEST_CURRENT_TEST` env var set | InMemory | pytest auto-sets this |
| `UMH_APPROVAL_BACKEND=memory` | InMemory | explicit override |
| `UMH_APPROVAL_BACKEND=test` | InMemory | explicit override |
| default (no env vars) | SQLite | production durability |

## Public API Preserved (zero breaking changes)

- `create_approval()` — unchanged signature
- `approve()` — unchanged signature
- `deny()` — unchanged signature
- `consume()` — unchanged signature
- `validate_for_execution()` — unchanged signature
- `get()` — unchanged signature
- `list_pending()` — unchanged signature
- `list_all()` — unchanged signature
- `get_counters()` — unchanged signature
- `reset()` — unchanged signature
- `get_approval_store()` — unchanged function (now lazy-initialized)
- `reset_approval_store(backend)` — NEW helper for tests

## Safety Constraints

1. No ExecutionRequest/ExecutionResult schema changes
2. No guard architecture changes
3. No new execution capabilities
4. No async/agents added
5. No shell allowlist broadening
6. SQLite WAL mode = safe concurrent reads
7. `busy_timeout=3000ms` prevents write contention failures
8. Parent directory auto-created at `data/runtime/`
9. Tests isolated via `PYTEST_CURRENT_TEST` detection (in-memory)

## Test Results

```
Phase 4F: 28 passed in 0.92s
Phases 4D+4E+4F+capabilities: 132 passed in 22.80s
Cross-process subprocess test: PASSED
```

Test coverage:
- A. SQLite basic operations (5 tests)
- B. Approve persists across instances (2 tests)
- C. Deny persists across instances (2 tests)
- D. Consume persists across instances (3 tests)
- E. Expired approvals persist (3 tests)
- F. Counters persist across instances (2 tests)
- G. CLI cross-process visibility (3 tests)
- H. In-memory backend still works (4 tests)
- I. Existing 4D approved execution still works (2 tests)
- J. SQLite isolation (2 tests)

## Validation Commands

```bash
python3 -c "import umh; print('OK')"          # OK
python3 -m umh.execution.approvals list        # No approvals found.
python3 -m umh.execution.metrics               # Shows approval counters
```

## What This Enables

- CLI (`python3 -m umh.execution.approvals`) now operates on durable state
- Runtime engine creates approvals that persist across restarts
- Future UI/API surfaces can read the same SQLite file
- No singleton sharing required between processes
- Approval lifecycle survives process crashes
