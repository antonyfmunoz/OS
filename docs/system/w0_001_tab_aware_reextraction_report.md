# W0-001 Tab-Aware API Re-Extraction Report

**Date**: 2026-05-04
**Status**: COMPLETE
**Method**: Google Docs API with includeTabsContent=true
**Backend**: API via gws CLI

---

## 1. Extraction Summary

| Metric | Value |
|--------|-------|
| Docs attempted | 28 |
| Docs extracted | 28 |
| Errors | 0 |
| Total tabs | 321 |
| Total child tabs | 134 |
| Total empty tabs | 72 |
| Total words | 283,831 |
| Prior extraction words | 22,431 |
| Words recovered | 261,400 |
| Prior coverage | 7.9% |
| Current coverage | 100% |

## 2. Per-Document Results

| Document | Tabs | Words | Prior Words | Coverage Change |
|----------|:----:|------:|:-----------:|:-:|
| LYFEOS | 53 | 44,400 | 255 | 0.6% → 100% |
| EntrepreneurOS | 14 | 40,222 | 740 | 1.8% → 100% |
| Coaching Philosophy/Methodology | 35 | 34,683 | 1,646 | 4.7% → 100% |
| CreatorOS | 8 | 27,301 | 0 | 0% → 100% |
| Systems Inventory (Virality Bible) | 20 | 22,695 | 1,833 | 8.1% → 100% |
| Coaching Frameworks & Workbooks | 30 | 19,800 | 1,446 | 7.3% → 100% |
| Antony F. Munoz (Personal Brand) | 21 | 19,070 | 1,647 | 8.6% → 100% |
| UMH | 8 | 13,949 | 963 | 6.9% → 100% |
| Conglomerate Brands | 15 | 11,487 | 1,487 | 12.9% → 100% |
| Empyrean Studios (Agency Brand) | 15 | 10,985 | 0 | 0% → 100% |
| Life Coaching (E-Learning) | 29 | 9,717 | 848 | 8.7% → 100% |
| Content | 25 | 9,226 | 813 | 8.8% → 100% |
| Untitled (coaching/outreach) | 7 | 4,233 | 1,440 | 34% → 100% |
| AI Tools | 5 | 2,677 | 29 | 1.1% → 100% |
| Hunter Hoffman - Service Contract | 1 | 2,672 | 2,672 | 100% |
| Untitled (UnifiedInfluence) | 4 | 2,119 | 426 | 20.1% → 100% |
| Business Template | 10 | 2,072 | 673 | 32.5% → 100% |
| Copy of Script Storytelling | 1 | 1,575 | 1,575 | 100% |
| Script Storytelling Structures | 1 | 1,575 | 1,575 | 100% |
| Untitled (dev setup) | 3 | 995 | 319 | 32.1% → 100% |
| Untitled (Hormozi) | 1 | 952 | 952 | 100% |
| Antony Munoz Email Sequence | 2 | 676 | 342 | 50.6% → 100% |
| Copy of Claude Cowork Plugins | 1 | 310 | 310 | 100% |
| SEMAX | 1 | 299 | 299 | 100% |
| Personal Curriculum | 8 | 106 | 106 | 100% |
| Untitled (SDK) | 1 | 35 | 35 | 100% |
| Automations | 1 | 0 | 0 | empty |
| AI Agents | 1 | 0 | 0 | empty |

## 3. Corrections Applied

| Issue | Prior State | Corrected State |
|-------|-------------|-----------------|
| CreatorOS | Marked "empty" | 27,301 words across 8 tabs |
| Empyrean Studios | Marked "empty" | 10,985 words across 15 tabs |
| LYFEOS | 255 words captured | 44,400 words (53 tabs) |
| EntrepreneurOS | 740 words captured | 40,222 words (14 tabs) |
| Total coverage | 7.9% (22,431w) | 100% (283,831w) |

## 4. Artifacts Produced

| Artifact | Location |
|----------|----------|
| Raw tab-aware JSON (28 files) | `data/drive_doc_ingestion_tab_aware/` |
| Canonical source records (28 files) | `data/canonical_source_records/w0_001/` |
| Source graph data | `data/canonical_source_records/w0_001/source_graph_data.json` |
| Redundancy register | `data/canonical_source_records/w0_001/redundancy_register.json` |
| Contradiction register | `data/canonical_source_records/w0_001/contradiction_register.json` |
| Extraction summary | `data/drive_doc_ingestion_tab_aware/extraction_summary.json` |
| Record index | `data/canonical_source_records/w0_001/_index.json` |

## 5. Prior Artifacts Superseded

The following W0-001 artifacts are now superseded by this tab-aware extraction:

| Artifact | Status |
|----------|--------|
| `data/drive_doc_ingestion/*.json` | SUPERSEDED (first-tab-only) |
| `docs/system/w0_001_source_graph_report.md` | SUPERSEDED (7.9% coverage) |
| `docs/system/w0_001_stale_assumption_contradiction_register.md` | SUPERSEDED |
| `docs/system/w0_001_redundancy_register.md` | SUPERSEDED (empty docs not empty) |
| `docs/system/w0_001_drive_document_review_report.md` | SUPERSEDED |

## 6. Gates

| Gate | Status |
|------|--------|
| Tab-aware API re-extraction | COMPLETE |
| Source graph rebuilt | COMPLETE |
| Contradiction register rebuilt | COMPLETE |
| Redundancy register rebuilt | COMPLETE |
| Memory promotion | BLOCKED (pending review) |
| CU document reader hardened | NOT YET (Track B) |

## 7. Next Step

Gate: `READY_FOR_MEMORY_PROMOTION_REVIEW_AFTER_TAB_AWARE_REEXTRACTION`

The full 283,831-word corpus is now extracted with complete tab coverage.
Founder review of the tab-aware outputs should precede memory promotion.
