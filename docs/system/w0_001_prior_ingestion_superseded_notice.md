# W0-001 Prior Ingestion — Superseded Notice

**Date**: 2026-05-04
**Reason**: First-tab-only extraction captured only 7.9% of actual content

---

## Superseded Artifacts

The following artifacts from the original W0-001 ingestion are now SUPERSEDED
by the tab-aware re-extraction completed on 2026-05-04:

| Artifact | Location | Issue |
|----------|----------|-------|
| First-pass JSON extractions | `data/drive_doc_ingestion/*.json` | First tab only, missing 92.1% |
| Document review report | `docs/system/w0_001_drive_document_review_report.md` | Based on 22,431w not 283,831w |
| Source graph report | `docs/system/w0_001_source_graph_report.md` | Incomplete entity coverage |
| Stale assumption register | `docs/system/w0_001_stale_assumption_contradiction_register.md` | Incorrectly flagged missing content as stale |
| Redundancy register | `docs/system/w0_001_redundancy_register.md` | Incorrectly marked 2 docs as empty |

## NOT Superseded

| Artifact | Reason |
|----------|--------|
| Tab coverage audit | Correctly identified the gap |
| API completeness correction | Correctly diagnosed the root cause |
| CU document review test plan | Still valid for CU hardening |
| CU document review sample report | Still valid (UMH tab detection proof) |
| Drive discovery inventory | Still valid (file list unchanged) |
| Computer use fallback proof (Drive) | Still valid (inventory CU proof) |

## Replacement Artifacts

| Superseded | Replaced By |
|-----------|-------------|
| `data/drive_doc_ingestion/*.json` | `data/drive_doc_ingestion_tab_aware/*.json` |
| `w0_001_drive_document_review_report.md` | `w0_001_tab_aware_drive_document_review_report.md` |
| `w0_001_source_graph_report.md` | `w0_001_tab_aware_source_graph_report.md` |
| `w0_001_stale_assumption_contradiction_register.md` | `w0_001_tab_aware_stale_assumption_contradiction_register.md` |
| `w0_001_redundancy_register.md` | `w0_001_tab_aware_redundancy_register.md` |

## Rule

Do not reference superseded artifacts for current intelligence.
Use tab-aware replacements exclusively.
Prior artifacts are retained for audit trail only.
