# Phase 95.1 — CU vs API Final Comparison Report

**Date**: 2026-05-04
**Work Order**: WO-LOCAL-PILOT-GDRIVE-GDOCS-001

---

## API Baseline (29 files)

The Google Drive API returned 29 files. These break into two categories:

### Category A: My Drive-Parented (26 files)
Files with `parents: ["0AMuKYpdP0e12Uk9PVA"]` (user's My Drive root)
and `owner_display: "Antony Munoz"`.

### Category B: Shared/No-Parent (3 files)
Files with `parents: []` and owned by external accounts.
These appear in "Shared with me" in the Drive UI, not in "My Drive".

| File | Owner | Modified |
|------|-------|----------|
| Antony Munoz Email Sequence | jeremy.ness | 2025-09-02 |
| Script Storytelling Structures | personalbrandlaunch | 2025-09-07 |
| SEMAX: The Brain Upgrade Nobody Talks About | connorsincoaching | 2025-09-07 |

## CU Inventory (26 files)

The computer-use inventory captured ALL 26 Category A files with 100%
precision (no false positives, no hallucinated items).

## Comparison Matrix

| CU Name | API Name | Match |
|---------|----------|:-----:|
| AI Agents | AI Agents | YES |
| AI Tools | AI Tools | YES |
| Antony F. Munoz (Personal Brand) | Antony F. Munoz (Personal Brand) | YES |
| Automations | Automations | YES |
| Business Template | Business Template | YES |
| Coaching Frameworks & Workbooks | Coaching Frameworks & Workbooks | YES |
| Coaching Philosophy/Methodology | Coaching Philosophy/Methodology | YES |
| Conglomerate Brands | Conglomerate Brands | YES |
| Content | Content | YES |
| Copy of Claude Cowork Plugins... | Copy of Claude Cowork Plugins... | YES |
| Copy of Script Storytelling Structures | Copy of Script Storytelling Structures | YES |
| CreatorOS | CreatorOS | YES |
| Empyrean Studios (Agency Brand) | Empyrean Studios (Agency Brand) | YES |
| EntrepreneurOS | EntrepreneurOS | YES |
| Hunter Hoffman - Service Contract | Hunter Hoffman - Service Contract | YES |
| Life Coaching (E-Learning/Info-Product) | Life Coaching (E-Learning/Info-Product) | YES |
| LyfeOS | LyfeOS | YES |
| LYFEOS_Product_Development_Roadmap.docx | LYFEOS_Product_Development_Roadmap.docx | YES |
| Personal Curriculum | Personal Curriculum | YES |
| Systems Inventory | Systems Inventory | YES |
| UMH | UMH | YES |
| Untitled document (×5, by date) | Untitled document (×5, by date) | YES |

**All 26 My Drive-parented files: MATCHED**

## Metrics

| Metric | Raw | Adjusted |
|--------|-----|----------|
| API baseline | 29 | 26 (My Drive only) |
| CU count | 26 | 26 |
| Recall | 89.7% | **100%** |
| Precision | 100% | 100% |
| F1 Score | 0.945 | 1.0 |

## Root Cause of Phase 95.0 "Gap"

The 89.7% recall in Phase 95.0 was **not a CU backend failure**.
It was a scope mismatch between:
- API query (returns all accessible files including shared)
- UI view ("My Drive" only shows owned + parented files)

The CU backend correctly captured everything visible in the UI.
No scroll, OCR, or backend repair was needed.

## Verdict

**COMPUTER_USE_FALLBACK_PROOF_ACCEPTED**

The CU observation path is complete and accurate for its scope.
To capture the 3 shared docs via CU, the system would need to
navigate to "Shared with me" — a separate UI action, not a scroll fix.
