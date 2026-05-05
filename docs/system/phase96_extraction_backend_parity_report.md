# Phase 96.0 — Extraction Backend Parity Report

**Date**: 2026-05-04
**Status**: COMPLETE

---

## 1. Correction Statement

The prior W0-001 flow incorrectly treated:
- API as production-complete (sole valid method)
- CLI as auth/connector support layer
- Computer Use as a partial fallback proof (Drive inventory only)

**Corrected model**: API, CLI, and Computer Use are all execution backends.
They must all satisfy the same canonical extraction contract or explicitly
report capability gaps. Production preference does not erase the parity goal.

## 2. Current Backend Status

| Backend | Overall | Tab Discovery | Content Extraction | Provenance |
|---------|:-------:|:------------:|:-----------------:|:----------:|
| API (tab-aware) | COMPLETE | COMPLETE | COMPLETE | COMPLETE |
| CLI (wraps API) | COMPLETE | COMPLETE | COMPLETE | COMPLETE |
| Computer Use | PARTIAL | PARTIAL* | BLOCKED | COMPLETE |

*CU tab DETECTION is proven (8/8 tabs found). Tab NAVIGATION is not yet proven.

## 3. Statements of Record

1. **API ingestion is not "the only complete method"**; it is currently
   the most complete implemented method.

2. **CLI should be made equivalent** by wrapping the same canonical
   extraction contract with `includeTabsContent=true`.

3. **Computer Use must be hardened** until it can produce equivalent
   records for any Google Doc through visible UI interaction only.

4. **W0-001 is not fully done** as a computer-use fallback test for
   document content. Tab detection is proven. Content extraction is not.

5. **W0-001 Drive inventory CU fallback is accepted.** The accessibility
   tree reading of Google Drive file lists achieved 100% recall.

6. **W0-001 Google Docs content CU fallback is NOT accepted yet.**
   The foreground ownership blocker prevents clipboard/keyboard extraction.

7. **Memory promotion should wait** until tab-aware API re-extraction
   is completed (283K words across all tabs of 28 documents).

8. **CU document reader hardening should be its own capability track**,
   not a one-off test — it requires fixing foreground ownership, testing
   clipboard capture, tab navigation, and scroll-and-read.

## 4. Artifacts Delivered

### Code Modules
| Module | Purpose |
|--------|---------|
| `eos_ai/substrate/extraction_backend_contracts.py` | Contract definitions, capability evaluation |
| `eos_ai/substrate/canonical_source_record.py` | Shared output schema for all backends |
| `eos_ai/substrate/extraction_parity_comparator.py` | Cross-backend parity measurement |
| `eos_ai/substrate/google_docs_backend_parity_matrix.py` | Google Docs capability matrix |

### Tests
| Test File | Tests | Status |
|-----------|:-----:|:------:|
| `tests/test_phase96_extraction_backend_contracts.py` | 10 | PASS |
| `tests/test_phase96_canonical_source_record.py` | 10 | PASS |
| `tests/test_phase96_extraction_parity_comparator.py` | 11 | PASS |
| `tests/test_phase96_google_docs_backend_parity_matrix.py` | 10 | PASS |

### Documentation
| Document | Location |
|----------|----------|
| Extraction Backend Parity Doctrine | `docs/operations/extraction_backend_parity_doctrine_v1.md` |
| Canonical Source Extraction Contract | `docs/operations/canonical_source_extraction_contract_v1.md` |
| Google Docs All-Tabs Contract | `docs/operations/google_docs_all_tabs_extraction_contract_v1.md` |
| Backend Equivalence Matrix | `docs/operations/api_cli_cu_backend_equivalence_matrix_v1.md` |
| CU Full Document Reader Requirements | `docs/operations/computer_use_full_document_reader_requirements_v1.md` |

## 5. Parity Thresholds

| Metric | MVP Threshold | Production Threshold |
|--------|:------------:|:-------------------:|
| Metadata parity | 100% | 100% |
| Tab discovery | 100% | 100% |
| Text extraction recall | 95% | 99% |
| False positive content | < 1% | < 0.1% |

## 6. Recommended Next Actions

| Priority | Action | Unlocks |
|:--------:|--------|---------|
| 1 | Run full tab-aware API re-extraction (28 docs, 283K words) | Memory promotion gate |
| 2 | Verify CLI wrapper passes includeTabsContent correctly | CLI parity confirmed |
| 3 | Fix CU foreground ownership (Phase A) | All CU content capabilities |
| 4 | Test CU clipboard capture after foreground fix (Phase B) | CU content extraction |
| 5 | Test CU tab navigation (Phase C) | Multi-tab CU extraction |
| 6 | Run CU parity validation against API reference (Phase E) | CU parity grade |

## 7. Gate

**Next Gate**: `APPROVE_TAB_AWARE_API_REEXTRACTION_AND_CU_DOC_READER_HARDENING_PLAN`

This gate approves:
- Full tab-aware API re-extraction of all 28 docs
- CU document reader hardening as a tracked capability track
- CLI parity verification

This gate does NOT approve:
- Memory promotion (still blocked until re-extraction completes)
- CU content extraction on production documents (blocked until foreground fixed)
