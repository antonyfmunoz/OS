# W0-001 Backend Parity Status After Re-Extraction

**Date**: 2026-05-04
**Status**: UPDATED

---

## 1. API Backend

| Metric | Status |
|--------|--------|
| Overall | **COMPLETE** |
| Tab-aware extraction | DONE (includeTabsContent=true) |
| All docs extracted | 28/28 |
| All tabs traversed | 321/321 |
| Child tabs traversed | 134/134 |
| Empty tabs marked | 72 (correct) |
| Total words | 283,831 |
| Canonical records produced | 28 |
| Parity reference | This IS the reference |

## 2. CLI Backend

| Metric | Status |
|--------|--------|
| Overall | **COMPLETE** |
| Method | gws CLI wrapping Google Docs API |
| Tab-aware | YES (passes includeTabsContent=true) |
| Parity with API | 100% (same underlying call) |
| Notes | CLI IS the API tool used for re-extraction |

## 3. Computer Use Backend

| Metric | Status |
|--------|--------|
| Overall | **PARTIAL** |
| Drive inventory | COMPLETE (100% recall) |
| Tab detection | COMPLETE (8/8 proven) |
| Tab navigation | BLOCKED (foreground) |
| Body text extraction | BLOCKED (foreground + canvas) |
| Scrolling | BLOCKED (foreground) |
| Clipboard capture | BLOCKED (foreground) |
| Canonical record output | NOT YET POSSIBLE |
| Parity with API | ~25% (metadata + tab detection only) |

## 4. Parity Gap Analysis

| Capability | API | CLI | CU | Gap |
|-----------|:---:|:---:|:--:|-----|
| Source inventory | ✓ | ✓ | ✓ | None |
| Document metadata | ✓ | ✓ | Partial | CU missing dates/owner |
| Tab discovery | ✓ | ✓ | ✓ | None (detection only) |
| Tab navigation | N/A | N/A | ✗ | Foreground blocked |
| Body extraction | ✓ | ✓ | ✗ | Foreground blocked |
| Child tabs | ✓ | ✓ | ? | Not tested |
| Provenance | ✓ | ✓ | ✓ | None |
| Canonical record | ✓ | ✓ | ✗ | Can't produce without content |

## 5. What Changed After Re-Extraction

| Before | After |
|--------|-------|
| API claimed "complete" on 22,431 words | API genuinely complete: 283,831 words |
| CLI status unclear | CLI confirmed complete (same tool) |
| CU gap: tab detection only | CU gap unchanged (foreground still blocks) |
| Parity unmeasurable | Parity measurable: API/CLI=100%, CU=~25% |

## 6. Hardening Requirements (CU only)

| Phase | Requirement | Blocks |
|-------|-------------|--------|
| A | Fix foreground ownership | Everything else |
| B | Clipboard content extraction | Full text capture |
| C | Tab navigation | Multi-tab extraction |
| D | Scroll-and-read | Long document capture |
| E | Parity validation | Backend graduation |

## 7. Recommended Next Steps

1. **Immediate**: Review tab-aware corpus for memory promotion readiness
2. **Next CU step**: Fix foreground ownership (Phase A of hardening plan)
3. **Validation**: After Phase A, test clipboard on single tab of UMH
4. **Full CU parity**: Requires all 5 phases — estimate 2-3 sessions

## 8. Next Gate

`READY_FOR_MEMORY_PROMOTION_REVIEW_AFTER_TAB_AWARE_REEXTRACTION`

Approving this gate means:
- Tab-aware corpus (283K words) is accepted as source of truth
- Memory promotion review can begin (reviewing what to promote)
- CU hardening proceeds as separate track (not blocking memory)
- Prior first-tab-only artifacts are officially superseded
