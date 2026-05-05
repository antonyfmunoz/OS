# Phase 5B: Identity + Scoped Authentication Layer — Audit Report

**Date:** 2026-04-26
**Status:** COMPLETE

## Files Changed

| File | Action |
|------|--------|
| `umh/control/identity.py` | NEW — Identity model, IdentityStore (SQLite + InMemory) |
| `umh/control/api.py` | Rewritten — identity-based auth, scope enforcement, actor injection |
| `umh/execution/approval.py` | Added `requested_by`, `approved_by` fields + `approved_by` param |
| `umh/execution/approval_persistence.py` | Added `update_actor`, new columns, schema migration |
| `tests/unit/test_phase5a.py` | Updated — 503→401 for unconfigured key (new auth behavior) |
| `tests/unit/test_phase5b.py` | NEW — 37 tests |

## Architecture

```
                     ┌──────────────────────────────┐
  API Request  ──→   │  Auth Middleware              │
  X-API-Key: ...     │    1. IdentityStore.authenticate()
                     │    2. Fallback: UMH_API_KEY   │
                     │    3. Attach identity to req  │
                     ├──────────────────────────────┤
                     │  Scope Check                  │
                     │    _require_scope(request, s) │
                     │    403 if missing scope       │
                     ├───���──────────────────────────┤
                     │  Endpoint Handler             │
                     │    identity.id → issued_by    │
                     │    identity.id → approved_by  │
                     │    identity.id → actor_id     │
                     └��─────────────────────────────┘
```

## Identity Model

```python
@dataclass
class Identity:
    id: str           # "id_<12hex>"
    name: str         # human-readable
    api_key_hash: str # sha256(raw_key)
    scopes: list[str] # permission set
    created_at: str   # ISO 8601
    status: str       # "active" | "disabled"
```

## Scopes

| Scope | Grants |
|-------|--------|
| `execute` | POST /execute |
| `approvals:read` | GET /approvals, GET /approvals/{id} |
| `approvals:write` | POST /approvals/{id}/approve, POST /approvals/{id}/deny |
| `metrics:read` | GET /metrics |
| `admin` | All of the above + identity management |

## API Key Lifecycle

1. `POST /identities` (admin only) → returns `api_key` once
2. Raw key is never stored — only `sha256(key)` persists
3. Authenticate: `sha256(provided) == stored_hash`
4. Disable: `POST /identities/{id}/disable` → auth permanently fails

## New Endpoints

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| POST | `/identities` | admin | Create new identity |
| GET | `/identities` | admin | List all identities |
| POST | `/identities/{id}/disable` | admin | Disable identity |

## Approval Actor Tracking

New fields on `ApprovalRequest`:
- `requested_by` — identity ID of the actor who triggered the operation
- `approved_by` — identity ID of the actor who approved

These fields are:
- Persisted in SQLite (new columns, auto-migrated)
- Included in `to_dict()` output
- Visible via GET /approvals and GET /approvals/{id}
- Set automatically by the API layer

## Execution Context Actor Injection

```python
context=ExecutionContext(metadata={"actor_id": identity.id})
issued_by=identity.id
```

Every execution through the API carries the identity ID in both
the execution context metadata and the `issued_by` field.

## Backwards Compatibility

- **Legacy UMH_API_KEY fallback**: If identity store auth fails, checks
  `UMH_API_KEY` env var. Legacy identity gets `admin` scope.
- **ApprovalRequest**: New fields have `""` defaults — no breaking change.
- **SQLite migration**: `ALTER TABLE ADD COLUMN` for existing databases.
- **All Phase 4D/4E/4F tests still pass**: 102 tests unchanged.

## Safety Constraints

1. No ExecutionRequest/ExecutionResult schema changes
2. No guard architecture modifications
3. API keys stored hashed (SHA-256), never in plaintext
4. `to_dict()` excludes `api_key_hash` from serialization
5. Disabled identities immediately lose all access
6. Scope enforcement at middleware level — endpoint code cannot bypass
7. No OAuth/JWT introduced (as specified)
8. No external services added

## Test Results

```
Phase 5B: 37 passed in 1.39s
Phases 5A+5B: 68 passed in 1.86s
All phases (4D+4E+4F+5A+5B+capabilities): 200 passed in 24.73s
```

Test coverage:
- A. Identity creation and auth (8 tests)
- B. API auth with identity keys (5 tests)
- C. Scope enforcement (7 tests)
- D. Identity attached to execution (2 tests)
- E. Approvals track actor (2 tests)
- F. Disabled identity blocked (2 tests)
- G. Identity management endpoints (6 tests)
- H. SQLite identity store persistence (4 tests)
- I. Full lifecycle with separate identities (1 test)

## Validation

```bash
python3 -c "import umh; print('OK')"          # OK
python3 -m umh.execution.approvals list        # No approvals found.
python3 -m umh.execution.metrics               # Shows counters
```
