# W0-001 Ingestion Lifecycle Status — Correction

**Phase**: 96.3-96.5  
**Status**: ACTIVE  
**Date**: 2026-05-04

---

## Core Summary

W0-001 tab-aware corpus (283,831 words, 321 tabs, 28 docs) has completed 5 of 8 lifecycle stages. Remaining stages are blocked by CU parity completion and founder review.

## Corpus Stats

| Metric | Value |
|--------|-------|
| Total words | 283,831 |
| Total tabs | 321 |
| Total documents | 28 |
| Backend used | Google Docs API (reference) |

## Lifecycle Progress

| Stage | Status | Notes |
|-------|--------|-------|
| DISCOVERED | COMPLETE | All 28 docs enumerated from Drive |
| AUTHORIZED | COMPLETE | API service account credentials valid |
| INGESTED_RAW | COMPLETE | Full tab-aware extraction via API |
| NORMALIZED | COMPLETE | Canonical record format applied |
| COVERAGE_VALIDATED | COMPLETE | 321/321 tabs extracted, 0 gaps |
| PARITY_VALIDATED | IN_PROGRESS | CU backend at ~25% parity with API reference |
| REVIEWED | BLOCKED | Requires founder review of corpus |
| PROMOTED | BLOCKED | Requires REVIEWED to complete first |

## Parity Status

- **API backend**: COMPLETE. Reference implementation. All 321 tabs extracted.
- **CU backend**: PARTIAL. ~25% of documents processed. Foreground browser fix required before further progress.
- **CLI wrapper**: COMPLETE extraction but LEVEL_0 independence (same failure domain as API — both use Google SDK).
- **MCP backend**: Not yet implemented.
- **Browser automation**: BLOCKED by proxy/bot detection.

## Memory Scope Assignment

- **Current scope**: INSTANCE_MEMORY — data is specific to the W0-001 workspace instance.
- **Global canon promotion**: NOT APPLICABLE until content is abstracted (raw details removed, privacy reviewed) and founder approves.
- **Rule**: All ingested data defaults to INSTANCE_MEMORY. Promotion to higher scopes requires explicit action.

## What Remains

1. **CU parity fix**: Resolve foreground browser requirement so CU can process remaining ~75% of documents.
2. **Founder review**: Per-document scope assignment — which docs promote to instance memory, which archive, which defer.
3. **Promotion**: After review, move approved documents to their assigned memory scopes.

## References

- `docs/system/w0_001_tab_aware_reextraction_report.md`
- `docs/system/w0_001_backend_parity_status_after_reextraction.md`
- `docs/system/w0_001_docs_tab_coverage_audit.md`
- `eos_ai/memory_scope.py`
- `eos_ai/instance_ingestion.py`
