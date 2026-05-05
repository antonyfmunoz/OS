# W0-001 CU Scroll Inventory Plan v1

**Status**: EXECUTED
**Date**: 2026-05-04
**Result**: Scrolling found 0 new items — all files already captured in initial read

---

## Scroll Strategy

1. Launch Chrome with `--force-renderer-accessibility` via Task Scheduler /IT
2. Wait for Drive page load (My Drive view)
3. Read initial accessibility tree DataItem elements
4. Focus DataGrid control (file list)
5. Send PageDown × 5 with 2s delays between each
6. Read accessibility tree after each scroll
7. Compare new items vs previous
8. Stop after 3 consecutive scrolls with 0 new items OR max scrolls reached

## Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| max_scrolls | 5 | 3 files missing → 1-2 scrolls should reveal them |
| scroll_delay_ms | 2000 | Allow Drive to render new rows |
| no_new_item_limit | 3 | Conservative — stop after 3 empty scrolls |
| scroll_key | {PGDN} | Standard page-down via SendKeys |
| focus_target | DataGrid | The file list table control |

## Outcome

Scrolling was unnecessary. The Chrome accessibility tree captured all 26
My Drive files in the initial read (before any scroll). The 3 "missing"
files exist in API but not in the My Drive UI view (they are shared docs
parented to other accounts).

## Lessons Learned

1. Chrome accessibility tree captures the full rendered DOM, not just the
   visible viewport — scrolling may not be needed for lists under ~50 items.
2. Drive virtual scroll only activates for large lists (100+ items).
3. Always verify API baseline categorization before assuming CU missed items.
4. The `parents` field in Drive API distinguishes owned vs shared files.
