# W0-001 Computer-Use Document Review Sample Report

**Date**: 2026-05-04
**Sample**: UMH (11p36P6TMvTnnz2KdQ2wYd3cDKfjHtCvVKp2_XEkuvz8)
**Status**: PARTIAL — Tab detection proven, content extraction needs hardening

---

## 1. Test Configuration

| Parameter | Value |
|-----------|-------|
| Chrome profile | Profile 5 |
| Chrome flags | --force-renderer-accessibility |
| Execution | Task Scheduler /IT (interactive session) |
| Target URL | docs.google.com/document/d/.../edit |
| Observation | Windows UI Automation |
| OS | Windows (DESKTOP-LVGUIQ9) |

## 2. Results

### Document Tab Detection: COMPLETE ✓

**8 tabs detected via ControlType.TreeItem:**

| # | Tab Name (CU) | Tab Name (API) | Match |
|---|---------------|----------------|:-----:|
| 1 | UNIVERSAL METS HARNESS | UNIVERSAL METS HARNESS | YES |
| 2 | Tab 2 | Tab 2 | YES |
| 3 | Tab 3 | Tab 3 | YES |
| 4 | Tab 4 | Tab 4 | YES |
| 5 | Tab 5 | Tab 5 | YES |
| 6 | Tab 6 | Tab 6 | YES |
| 7 | Tab 7 | Tab 7 | YES |
| 8 | Tab 8 | Tab 8 | YES |

**Tab detection recall: 100% (8/8)**
**Tab name accuracy: 100%**

### Content Extraction: FAILED

| Approach | Result | Reason |
|----------|--------|--------|
| ControlType.Text elements | 5 elements, 20 words (toolbar text only) | Google Docs canvas rendering |
| TextPattern on Document | Returned menu/toolbar text | Not document content |
| Ctrl+A / Ctrl+C clipboard | Empty clipboard | SetForegroundWindow failed |
| Scroll + accumulate | No new elements | Keystrokes not delivered |

### Root Cause

Windows does not allow a process that doesn't own the foreground to
steal it from another process. The Task Scheduler /IT process is in
the user's interactive session but is not the foreground window owner.
Chrome retains foreground. SendKeys targets foreground window → wrong target.

## 3. Compliance

| Rule | Status |
|------|--------|
| API used for live CU extraction | NO |
| Playwright | NO |
| CDP | NO |
| Screenshots stored | NO |
| Documents edited | NO |
| Credentials captured | NO |
| Gmail accessed | NO |
| Accounts switched | NO |

## 4. CU vs API Comparison (Tab Detection Only)

| Metric | CU | API | Match |
|--------|----|----|:-----:|
| Total tabs | 8 | 8 | YES |
| Tab names | All matched | — | YES |
| Content words | 0 (not extracted) | 13,949 | N/A |
| Content coverage | 0% | 100% | — |

## 5. Assessment

**Computer-use document review is PARTIALLY proven:**
- Tab detection: COMPLETE and ACCURATE
- Content extraction: REQUIRES HARDENING

The foreground ownership issue is a solvable engineering problem,
not a fundamental limitation. Once the Chrome launch and reader script
run in the same task (same process owns foreground), clipboard extraction
should work because Google Docs' Ctrl+A/Ctrl+C is well-known to copy
full document content to clipboard.

## 6. Conclusion

The CU fallback for document review is **not yet production-ready**
but the foundational capability (tab detection, window identification,
accessibility tree reading) is proven. The remaining gap is a Windows
process-level issue (foreground ownership) that has known solutions.

**Recommendation**: Accept API ingestion as production method.
Keep CU tab detection as proven fallback metadata layer.
Harden CU content reader in a future phase if needed.
