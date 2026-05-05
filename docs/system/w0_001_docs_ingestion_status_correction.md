# W0-001 Document Ingestion Status Correction

**Date**: 2026-05-04
**Prior Claim**: 28/28 docs ingested, 22,474 words, ingestion complete
**Corrected Status**: 28/28 first-tabs read; 261,400 words missed (92.1%)

---

## 1. Correction Summary

| Metric | Prior Claim | Actual |
|--------|-------------|--------|
| Docs read | 28/28 | 28/28 (first tab only) |
| Words captured | 22,474 | 22,431 (first tab) |
| Actual total words | (not measured) | 283,831 |
| Coverage | "complete" | 7.9% |
| Empty docs | 4 | 2 (CreatorOS + Empyrean Studios have content in tabs) |
| Multi-tab docs | (not checked) | 19 of 28 |

## 2. Method Separation (Clarified)

### Production Ingestion (API)
- **Method**: Google Docs API via GWS CLI with `includeTabsContent=true`
- **Coverage**: 100% — all tabs, recursive childTabs
- **Speed**: Fast (batch-processable)
- **Reliability**: High (structured JSON)
- **Status**: READY (corrected API call pattern proven in tab audit)

### Computer-Use Fallback
- **Method**: Chrome + UIAutomation + Task Scheduler /IT
- **Coverage**: Tab detection 100%, content extraction 0% (needs hardening)
- **Speed**: Slow (single-document, sequential)
- **Reliability**: Low (depends on foreground ownership, window positioning)
- **Status**: Tab detection PROVEN, content reader NEEDS HARDENING

## 3. What The Prior CU Fallback Test Proved

| Capability | Phase | Status |
|-----------|-------|--------|
| Drive file list inventory | 95.0-95.1 | PROVEN (100% recall) |
| Drive file metadata extraction | 95.0 | PROVEN (name, type, date) |
| Chrome accessibility tree reading | 95.0-95.1 | PROVEN |
| Task Scheduler /IT execution | 95.0-95.1 | PROVEN |
| Google Doc tab detection | W0-001R | PROVEN (8/8 tabs) |
| Google Doc content extraction | W0-001R | NOT PROVEN (foreground issue) |
| Google Doc tab navigation | W0-001R | NOT ATTEMPTED |
| Google Doc scrolling/reading | W0-001R | NOT PROVEN |

## 4. Impact on Prior Deliverables

| Deliverable | Status | Action |
|-------------|--------|--------|
| `data/drive_doc_ingestion/*.json` | First-tab-only | Re-extract with tabs |
| `data/drive_doc_ingestion/document_summaries.json` | Incomplete | Rebuild after re-extraction |
| `docs/system/w0_001_source_graph_report.md` | Partially invalid | Rebuild after re-extraction |
| `docs/system/w0_001_stale_assumption_contradiction_register.md` | Partially invalid | Re-evaluate |
| `docs/system/w0_001_redundancy_register.md` | Invalid (empty docs aren't empty) | Rebuild |
| `docs/system/w0_001_ingestion_queue_next_sources.md` | Still valid | No change needed |
| `docs/system/w0_001_drive_document_review_report.md` | Superseded | This correction replaces |
| `docs/system/w0_001_computer_use_fallback_proof_acceptance.md` | Still valid for Drive inventory | Scope clarified |

## 5. Corrected Ingestion Pipeline

```
APPROVED PRODUCTION PIPELINE:
gws docs documents get --params '{"documentId": "<ID>", "includeTabsContent": true}'
  → parse response.tabs (NOT response.body)
  → for each tab: extract tab.documentTab.body
  → recursively traverse childTabs
  → preserve provenance: tabId, title, depth, parentPath
  → store per-tab extraction records

CU FALLBACK PIPELINE (NOT YET PRODUCTION-READY):
Chrome --force-renderer-accessibility → Google Doc
  → UIAutomation reads TreeItem elements (tab detection)
  → [BLOCKED: foreground ownership needed for content read]
  → [FUTURE: fix foreground → Ctrl+A/C → clipboard]
```

## 6. Gate Status

| Gate | Status |
|------|--------|
| COMPUTER_USE_FALLBACK_PROOF_ACCEPTED | VALID (Drive inventory) |
| READY_FOR_TARGETED_DOCUMENT_REVIEW_APPROVAL | EXECUTED (first-tab-only) |
| Tab coverage audit | COMPLETE |
| CU document review sample | PARTIAL (tab detection only) |
| Full tab-aware re-extraction | PENDING APPROVAL |
| READY_FOR_MEMORY_PROMOTION_REVIEW | **BLOCKED** until re-extraction |

## 7. Decision Required

The founder must decide:

**A: ACCEPT_API_INGESTION_WITH_CU_FALLBACK_SAMPLE**
- Accept API (tab-aware) as production ingestion method
- Accept CU tab detection as proven fallback metadata layer
- Proceed with full tab-aware re-extraction
- Defer CU content reader hardening to a future phase

**B: APPROVE_FULL_CU_DOCUMENT_REVIEW**
- Harden CU reader first (fix foreground + clipboard)
- Run full CU content extraction for all 28 docs
- Compare CU vs API for validation
- Significantly more time-intensive

**C: HARDEN_VISIBLE_GOOGLE_DOC_READER**
- Fix the foreground ownership issue first
- Re-run CU sample on UMH with working clipboard
- Then decide whether to proceed with full CU review

**D: PAUSE_MEMORY_PROMOTION**
- Block all memory promotion until tab-aware re-extraction is complete
- Rebuild source graph, assumption register, and redundancy register
- Then proceed to memory promotion review
