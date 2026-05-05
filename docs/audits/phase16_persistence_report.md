# Phase 16 Audit Report — Durable Persistence + Replayable Runtime State v1

**Date:** 2026-04-29
**Status:** PASS — all invariants verified
**Tests:** 47/47 passed | Regression: 477/477 passed (phases 11B–16, zero regressions)

---

## Deliverables

| # | Deliverable | File | Status |
|---|-------------|------|--------|
| 1 | `JobPersistenceBackend` Protocol | `umh/jobs/persistence.py` | DONE |
| 2 | `FileJobPersistenceBackend` (atomic writes) | `umh/jobs/persistence.py` | DONE |
| 3 | `JobStore` persistence integration | `umh/jobs/store.py` | DONE |
| 4 | `RuntimeBootstrap` + `BootstrapReport` | `umh/runtime/bootstrap.py` | DONE |
| 5 | `umh/runtime/__init__.py` exports | `umh/runtime/__init__.py` | DONE |
| 6 | `umh/jobs/__init__.py` exports | `umh/jobs/__init__.py` | DONE |
| 7 | Test suite | `tests/unit/test_phase16_persistence.py` | DONE — 47 tests |

---

## Hard Invariants

| # | Invariant | Verified |
|---|-----------|----------|
| 1 | Cells NEVER execute — no subprocess, no shell, no dangerous stdlib calls | YES — AST boundary test |
| 2 | No shell=True anywhere in persistence or bootstrap | YES — AST boundary test |
| 3 | persistence.py imports only models + stdlib | YES — import test |
| 4 | bootstrap.py imports only lifecycle, models, store | YES — import test |
| 5 | No imports from umh/cells, umh/environments, umh/adapters | YES — source scan |
| 6 | All status mutations via lifecycle.transition() | YES — store._transition() enforces |
| 7 | Atomic writes: tempfile → fsync → os.replace | YES — code review + tests |
| 8 | Corrupted files skipped, never fatal | YES — test_corrupted_file_skipped |
| 9 | Persistence errors non-fatal in JobStore | YES — bare except in _persist/_rehydrate |
| 10 | RUNNING → ORPHANED on bootstrap restart | YES — test_running_becomes_orphaned |
| 11 | ORPHANED with retries → SUBMITTED | YES — test_retry_on_rehydrate |
| 12 | SUCCEEDED/CANCELLED untouched | YES — test_succeeded_untouched |
| 13 | CREATED/SUBMITTED preserved | YES — test_submitted_preserved |
| 14 | No execution during replay | YES — test_no_execution_during_replay |
| 15 | JobPersistenceBackend is @runtime_checkable Protocol | YES — isinstance test |
| 16 | FileJobPersistenceBackend satisfies Protocol | YES — isinstance test |
| 17 | job_id sanitized (no path traversal) | YES — _job_path replaces / and .. |
| 18 | Backward compatibility — JobStore works without persistence | YES — all Phase 15 tests pass |
| 19 | RuntimeLoop unchanged — no new constructor params this phase | YES — code review |

---

## Architecture

```
JobStore (store.py)
  ├── _persistence: JobPersistenceBackend | None
  ├── _rehydrate() → loads all persisted jobs on init
  └── _persist(job) → saves after every valid transition

FileJobPersistenceBackend (persistence.py)
  ├── save_job() → atomic: tempfile → fsync → os.replace
  ├── load_job() / load_all_jobs() → JSON parse with error resilience
  └── delete_job() → unlink with FileNotFoundError tolerance

RuntimeBootstrap (bootstrap.py)
  └── rehydrate(store) → classifies all jobs, fixes RUNNING→ORPHANED,
      retries eligible, returns BootstrapReport
```

---

## Test Coverage Summary

| Category | Count | Description |
|----------|-------|-------------|
| Persistence backend | 14 | save/load/delete, round-trip, corruption, path safety |
| Store with persistence | 6 | rehydrate on init, persist on transitions, delete |
| Bootstrap / replay | 8 | orphan detection, retry, terminal preservation, error handling |
| Runtime integration | 5 | round-trip, state transitions, replay safety |
| Boundary invariants | 8 | no cells import, no subprocess, no shell=True, protocol checks |
| Regression | 6 | all Phase 15 transitions still work with persistence=None |
| **Total** | **47** | |

---

## Regression

Full suite: 477 tests across phases 11B–16. Zero failures. Zero regressions.

| Phase | Tests | Result |
|-------|-------|--------|
| 11B–11F | 259 | PASS |
| 12 | 49 | PASS |
| 13 | 55 | PASS |
| 14 | 50 | PASS |
| 15 | 17 | PASS |
| 16 | 47 | PASS |
| **Total** | **477** | **PASS** |

---

## Files Modified/Created

| File | Action |
|------|--------|
| `umh/jobs/persistence.py` | CREATED — 129 lines |
| `umh/jobs/store.py` | MODIFIED — added persistence backend integration |
| `umh/runtime/bootstrap.py` | CREATED — 133 lines |
| `umh/runtime/__init__.py` | MODIFIED — added BootstrapReport, RuntimeBootstrap exports |
| `umh/jobs/__init__.py` | MODIFIED — added FileJobPersistenceBackend, JobPersistenceBackend exports |
| `tests/unit/test_phase16_persistence.py` | CREATED — 47 tests |
| `docs/audits/phase16_persistence_report.md` | CREATED — this file |
