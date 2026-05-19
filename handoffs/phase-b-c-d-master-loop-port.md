# Handoff: Phase B/C/D — Master Loop Port to services/umh

**Date:** 2026-05-19
**Branch:** feature/master-loop-composition
**Status:** Phase D verification complete. Phase E NOT started.

---

## What was done

Ported the ExecutionPipeline (master success loop) from the parallel
`umh_mvp/` implementation into the canonical `services/umh/` codebase.
Three phases completed in sequence:

- **Phase B** — Built `ExecutionPipeline` + `MemoryPromoter` in services/umh
- **Phase C** — Ported 43 tests from umh_mvp/tests/ (5 test files)
- **Phase D** — Full verification (48/48 pytest + import check + manual
  signal-to-outcome through real subsystems)

## Files created/modified

| File | Action | Purpose |
|------|--------|---------|
| `services/umh/control_plane/pipeline.py` | **NEW** (243 lines) | 10-stage master success loop: signal → governance → work packet → execute → proof → outcome → trace → memory candidate → memory promote → resume state |
| `services/umh/memory/promoter.py` | **NEW** (95 lines) | Confidence-threshold + content-hash dedup promotion from candidates to durable JSON store |
| `services/umh/memory/__init__.py` | **UPDATED** | Added MemoryPromoter export |
| `services/umh/orchestrator.py` | **UPDATED** | `execute_trace()` docstring marked DEPRECATED in favor of `ExecutionPipeline.submit_signal()` |
| `services/umh/tests/test_layer0.py` | **NEW** (10 tests) | Foundation ontology completeness |
| `services/umh/tests/test_governance.py` | **NEW** (7 tests) | PolicyEngine risk evaluation |
| `services/umh/tests/test_pipeline.py` | **NEW** (6 tests) | Master loop stages |
| `services/umh/tests/test_integration.py` | **NEW** (6 tests) | Multi-signal E2E + audit trail |
| `services/umh/tests/test_extensions.py` | **NEW** (13 tests) | Adapters, approval workflow, promoter, workstation |

## Test coverage

**48 tests pass** (42 ported + 6 existing canary).

The 1-test delta from umh_mvp's 43: the AdapterRegistry.find(packet)
test was not ported because services/umh's executor uses direct
adapter registration (no registry indirection). Architecturally correct.

| File | Count | Domain |
|------|-------|--------|
| test_e2e.py | 6 | Existing canary (unchanged) |
| test_layer0.py | 10 | Foundation: ontology, laws, epistemology |
| test_governance.py | 7 | PolicyEngine: all 8 risk classes |
| test_pipeline.py | 6 | Master loop stages + events |
| test_integration.py | 6 | Multi-signal E2E + audit trail |
| test_extensions.py | 13 | Adapters, approval, promoter, workstation |

## Verification results (Phase D)

1. `pytest services/umh/tests/ -v` — **48 passed, 0 failed** (0.26s)
2. Import check — `ExecutionPipeline` instantiates with real `PolicyEngine` + `WorkPacketExecutor`
3. Manual signal-to-outcome — `echo hello` through full pipeline:
   - governance_approved: True (read-only auto-approved)
   - executed: True, success: True
   - proof_id: generated
   - outcome_type: success
   - memory_candidate_id: generated
   - memory_promoted: True

## Architecture decisions locked in

1. **services/umh protocols are canonical** — richer UUID-based types, two-tier risk (RiskClass → RiskLevel)
2. **Sync pipeline + sync event emission** — on_event() callbacks at every stage, WebSocket bridge later
3. **Dual-write trace** — protocol Trace (event-sourced structural truth) + JSONL TraceStore (queryable projection)
4. **Pre-approved override** — pre_approved=True bypasses governance with audit trail preserved
5. **Blocked signals still traced** — governance-denied signals produce JSONL trace records

## Still standing

- **`Orchestrator.execute_trace()`** — deprecated wrapper, retained for backward compat with 6 existing test_e2e.py tests. Will be removed when callers migrate to `ExecutionPipeline.submit_signal()`.
- **`umh_mvp/`** — entire parallel implementation still alive, untouched. Awaiting Phase E retirement decision.
- **`/opt/OS/control_plane/protocols/`** — umh_mvp's protocol layer, orphaned from services/umh. Phase E cleanup target.

## CRITICAL: Phase E gate

**Do NOT auto-proceed to Phase E (umh_mvp retirement) in the next session.**
Antony must decide whether to keep umh_mvp/ alive for comparison testing
during early integration work. This is an explicit hold.
