# Legacy Test Archive — 2026-05-14

## Reason

These 82 test files contain 194 imports from `runtime.substrate.*` or
`eos_ai.*` — paths deleted in Wave 6 of the §24 migration (commits
`8454a648` and `1c320aaf`). The tests are broken by design after shim
deletion and have no production value. Canonical §24 test coverage now
lives in `tests/migration/`.

## Source paths

- `tests/test_phase94d*` — phase 94D governance/topology/adapter tests (19 files)
- `tests/test_phase95*` — phase 95 GUI/drive/local control tests (5 files)
- `tests/test_phase96*` — phase 96 extraction/backend/MCP tests (14 files)
- `tests/test_w0_*` — W0 execution/doc-reader tests (8 files)
- `tests/test_execution_adapter.py`, `tests/test_execution_router.py` (2 files)
- `tests/integration/transport/` — substrate smoke/integration tests (23 files)
- `tests/test_phase965_*` — adapter engine/quality tests (4 files)
- `tests/test_phase966_*` — tool mastery/terminology tests (3 files)
- Remaining phase 96.4/96.8 tests (4 files)

Total: 82 files, 194 legacy imports.

## Stragglers retained (NOT archived)

These 6 files mixed legacy + canonical imports. Each had one
`runtime.substrate.*` import alongside canonical §24 imports.

**RESOLVED 2026-05-14** (`5e909bb6`): All 6 updated to canonical
`runtime.transport.*` paths. Zero legacy imports remain in `tests/`.

| File | Legacy imports | Canonical imports |
|------|---------------|-------------------|
| `tests/test_w0_execution_binding.py` | 1 | 5 |
| `tests/test_local_worker_visible_chrome_gate.py` | 1 | 3 |
| `tests/test_foreground_cu_ingestion_execution_v1.py` | 1 | 8 |
| `tests/test_founder_visual_confirmation_gate.py` | 1 | 1 |
| `tests/test_local_worker_runtime_daemon.py` | 1 | 1 |
| `tests/test_w0_coherence_envelope.py` | 1 | 5 |

## Canonical test coverage

Migration tests: `tests/migration/` — 93 passed, 1 deselected.
These pin all §24 behavioral contracts and are unaffected by this archive.

## Per triage manifest Row 82
