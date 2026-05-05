# W0-001 API Ingestion Completeness Correction

**Date**: 2026-05-04
**Status**: CORRECTION REQUIRED
**Prior Status**: Incorrectly marked as 28/28 COMPLETE
**Actual Status**: 28/28 docs read, but only first tab per doc (7.9% coverage)

---

## 1. What Was Wrong

The prior ingestion (W0-001 document review) reported:
- "28/28 Google Docs read — 0 errors"
- "22,474 total words ingested"
- "4 empty placeholder docs"

**Actual reality:**
- 28/28 docs had their FIRST TAB read — NOT all content
- Actual total content: **283,831 words** across all tabs
- Only **22,431 words** captured (7.9%)
- 2 docs marked "empty" actually contain 38,286 words combined
- 19 of 28 docs have multiple tabs that were silently skipped

## 2. Root Cause

Google Docs API call without `includeTabsContent=true` only returns
the first tab's content in `document.body`. Multi-tab documents
(introduced in Google Docs 2024) are silently truncated.

The GWS CLI call used:
```
gws docs documents get --params '{"documentId": "..."}'
```

Should have been:
```
gws docs documents get --params '{"documentId": "...", "includeTabsContent": true}'
```

## 3. Impact on Prior Reports

### Source Graph (w0_001_source_graph_report.md)
- **PARTIALLY INVALID** — built on 7.9% of content
- Entity/relationship graph is incomplete
- Frameworks, products, and offers have undiscovered content in tabs

### Stale Assumption Register
- **PARTIALLY INVALID** — may have flagged things as "stale" that
  are actually developed in non-first tabs

### Redundancy Register
- **REQUIRES RE-EVALUATION** — docs marked "empty" (CreatorOS,
  Empyrean Studios) actually contain 38K+ words

### Document Summaries
- **INCOMPLETE** — summaries based on first-tab-only content

## 4. Corrective Action Status

| Action | Status |
|--------|--------|
| Tab audit completed | YES (this report) |
| Tab-aware word counts verified | YES |
| Full tab-aware text re-extraction | PENDING (approved for completeness) |
| Source graph rebuild | PENDING (after re-extraction) |
| Stale assumption re-evaluation | PENDING (after re-extraction) |
| Redundancy register rebuild | PENDING (after re-extraction) |

## 5. Method Separation

| Method | Purpose | Status |
|--------|---------|--------|
| Google Docs API (tab-aware) | Production ingestion | APPROVED, ready |
| Computer-use (UIAutomation) | Worst-case fallback | Tab detection proven, content extraction needs hardening |

The API connector with `includeTabsContent=true` is the correct
production method for document content ingestion.

Computer-use proved:
- Drive file list inventory (100% recall for My Drive)
- Google Docs tab detection via accessibility tree (8/8 tabs found)
- Content extraction blocked by Windows foreground limitation

## 6. Recommended Next Step

Perform a full tab-aware re-extraction of all 28 docs using the
corrected API call. This will produce ~283K words of source material
that can then be properly analyzed for the source graph, assumptions,
and redundancy registers.
