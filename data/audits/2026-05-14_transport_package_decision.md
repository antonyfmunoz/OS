# Transport Package §24 Migration — Decision Record

Date: 2026-05-14

## Decision 1: Target Layer

**Choice:** `execution/transport/`

**Rationale:**
- §24 canonical tree defines `execution/` with `actions/ work_packets/ queue/ dag/ workers/ environments/ actuation/ runtime/`
- Transport is execution infrastructure: sessions, storage, station daemon, capability tagging
- `execution/` already exists and holds other runtime execution machinery
- No new top-level directory needed — fits the established pattern

**Rejected alternatives:**
- `adapters/transport/` — transport is not an adapter in the §24 sense (it doesn't bridge UMH to external systems)
- Top-level `transport/` — would add a new slot not in synthesis §24

## Decision 2: Migration Approach

**Choice:** BIG-BANG (sub-batched by logical group)

**Rationale:**
- Only 11 PROD callers (very manageable)
- Zero mock patches by string path
- One dynamic importlib call (in a smoke test — archivable)
- `__init__.py` is only 64 lines with simple `_LAZY_MAP` — trivial to update
- No complex shim replication needed
- 68 smoke tests — bulk classifiable as UPDATE vs ARCHIVE

**Safety net:** A thin re-export shim left at `runtime/transport/__init__.py` handles:
1. The conftest namespace resolution requirement
2. Any undiscovered try/except guarded imports in production code
3. Third-party or dynamic references we couldn't grep for

The shim delegates via `__getattr__` to `execution.transport` — it does NOT duplicate the lazy-import `_LAZY_MAP` logic.

## Caller Surface (at time of migration)

| Category | Count | Action |
|----------|-------|--------|
| PROD | 11 | Updated to `execution.transport` |
| TEST | 3 | Updated to `execution.transport` (conftest kept as shim user) |
| SMOKE | 68 | 23 archived (reference archived modules), 45 updated |
| INTRA_TRANSPORT | 57 | Moved with package (249 internal refs updated) |
| Mock patches | 0 | N/A |
| Dynamic importlib | 1 | Updated |
