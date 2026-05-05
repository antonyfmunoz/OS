# Phase 82 — Storage + Memory Discipline v1

## Summary

Phase 82 hardens UMH's persistence boundary. All durable system state
now flows through explicit storage contracts, a disciplined gateway,
memory write validation, and policy enforcement. No auto-promotion.
No delete. Append-only where it matters. Mutable only where allowed.

## Counts

| Metric | Count |
|--------|-------|
| New files created | 9 |
| Existing files modified | 13 |
| Tests | 139 |
| Storage record types | 21 |
| Storage operations | 9 |
| Memory record types | 11 |
| Memory statuses | 7 |
| Invariants enforced | 8 tested |
| API endpoints added | 7 |
| CLI commands added | 6 |

## New Files

| File | Purpose |
|------|---------|
| `umh/storage/contracts.py` | Typed envelopes: StorageRecordType, scope, mutability, source, backend, operations |
| `umh/storage/policy.py` | Mutability classification, operation evaluation, deny/allow rules |
| `umh/storage/gateway.py` | Disciplined gateway wrapping all write paths with policy enforcement |
| `umh/storage/audit.py` | Read-only scanner for persistence boundary bypasses |
| `umh/storage/views.py` | StorageDescriptorView, StorageHealthView, StorageAuditView |
| `umh/memory/discipline.py` | Memory types, scopes, statuses, write policy, candidate classification |
| `umh/memory/promotion_policy.py` | Promotion decisions — disabled by default, requires future engine |
| `umh/memory/write_validator.py` | Validates all memory writes before storage |
| `umh/memory/views.py` | MemoryCandidateDisciplineView, MemoryDisciplineHealthView |

## Modified Files

| File | Change |
|------|--------|
| `umh/control/trace_store.py` | Added `export_storage_descriptors()` |
| `umh/feedback/store.py` | Added `export_storage_descriptors()` |
| `umh/workstation/session_state.py` | Added `export_storage_descriptors()` |
| `umh/workstation/device_registry.py` | Added `export_storage_descriptors()` |
| `umh/workstation/environment_registry.py` | Added `export_storage_descriptors()` |
| `umh/ontology/primitives.py` | Added `export_storage_descriptors()` |
| `umh/ontology/laws.py` | Added `export_storage_descriptors()` |
| `umh/registry/catalog.py` | Added `export_storage_descriptors()` |
| `umh/observability/system_status.py` | Added storage_gateway_status, memory_discipline_status, checker functions |
| `umh/observability/operator_views.py` | Added storage_summary, memory_discipline_summary to dashboard |
| `umh/interface/views.py` | Added storage_summary, memory_discipline_summary to OperatorDashboardSnapshot |
| `umh/control/api.py` | Added 7 GET endpoints for storage/memory discipline |
| `umh/control/cli.py` | Added 6 CLI commands for storage/memory discipline |

## Key Design Decisions

1. **No auto-promotion**: Memory candidates stay as NEEDS_REVIEW. Promotion requires a future promotion engine with human review.
2. **Delete always denied**: No record type allows DELETE through the gateway.
3. **Append-only enforcement**: TRACE, OUTCOME, FEEDBACK, AUDIT_RECORD, SYSTEM_REPORT deny UPDATE/PROMOTE.
4. **Immutable types**: ONTOLOGY_PRIMITIVE, ONTOLOGY_LAW, DOMAIN_PROJECTION, CORRESPONDENCE_MAP deny all writes.
5. **Additive store compatibility**: Existing stores gained `export_storage_descriptors()` without breaking existing APIs.
6. **Gateway wraps, doesn't replace**: The StorageGateway enforces policy and logs all operations but delegates to existing backends.

## Verification

```bash
# Run all 139 tests
python3 -m pytest tests/test_phase82_storage_memory_discipline.py -v

# Compile-check all new files
python3 -m py_compile umh/storage/contracts.py
python3 -m py_compile umh/storage/policy.py
python3 -m py_compile umh/storage/gateway.py
python3 -m py_compile umh/storage/audit.py
python3 -m py_compile umh/storage/views.py
python3 -m py_compile umh/memory/discipline.py
python3 -m py_compile umh/memory/promotion_policy.py
python3 -m py_compile umh/memory/write_validator.py
python3 -m py_compile umh/memory/views.py

# CLI smoke test
python3 -m umh.control.cli storage-status --json
python3 -m umh.control.cli storage-policy --json
python3 -m umh.control.cli memory-discipline-status --json
```

## Invariants Tested

- INV-521: Append-only types deny UPDATE
- INV-522: DELETE always denied for all record types
- INV-523: Auto-promotion disabled by default
- INV-524: Immutable types deny all writes
- INV-525: Gateway enforces policy on every write (audit log)
- INV-526: READ always allowed for all types
- INV-527: PROMOTE on PROMOTABLE requires future engine
- INV-528: MemoryRecord from candidate starts as NEEDS_REVIEW
