# W-GDOCS-CU-001 Hardening Run Report

Phase: 96.7G
Date: 2026-05-05
Package: W-GDOCS-CU-001

## Environment

- Execution node: Linux VPS (orchestrator)
- Local worker: NOT REACHABLE from VPS
- Preflight status: WRONG_HOST
- Live CU execution: NOT POSSIBLE from this node

## Current Maturity: 56.2% (9/16 checks)

### Capabilities Present (from Phase W0-001R proof)

| Capability | Status |
|-----------|--------|
| GUI ownership | PROVEN |
| Browser profile | PROVEN |
| Account verified | PROVEN |
| Docs openable | PROVEN |
| Tabs detectable (8/8) | PROVEN |
| Per-doc provenance | PROVEN |
| Governance clean | PROVEN |
| Tool mastery | PROVEN |
| Tests present | PROVEN |

### 7 Remaining Gaps

| Gap | Blocker |
|-----|---------|
| child_tabs_supported | Not implemented |
| content_extractable | Windows foreground ownership blocks extraction |
| scrolling_complete | Cannot verify without content extraction |
| per_tab_provenance_complete | Requires tab-level extraction |
| empty_tabs_marked | Not implemented |
| inaccessible_tabs_marked | Not implemented |
| parity_against_api | Requires content extraction to compare |

### Hardening Work Orders

- WO-GDOCS-CU-CHILD_TABS_SUPPORTED
- WO-GDOCS-CU-CONTENT_EXTRACTABLE
- WO-GDOCS-CU-SCROLLING_COMPLETE
- WO-GDOCS-CU-PER_TAB_PROVENANCE_COMPLETE
- WO-GDOCS-CU-EMPTY_TABS_MARKED
- WO-GDOCS-CU-INACCESSIBLE_TABS_MARKED
- WO-GDOCS-CU-PARITY_AGAINST_API

## Root Blocker

Windows foreground ownership: Task Scheduler /IT process does not own
the foreground window. Content extraction (SendKeys, clipboard) requires
foreground focus. Tab detection works because accessibility tree reads
do not require foreground ownership.

## Status: PARTIAL_NEEDS_HARDENING

Live CU hardening was not possible from VPS. The 7 gaps require
local Windows desktop execution with foreground ownership solved.

## Parity Baseline Required

| Metric | Target |
|--------|--------|
| Docs | 28 |
| Tabs | 321 |
| Child tabs | 134 |
| Words | 283,831 |

## Code Reference

- Module: core/adapter_package_manager/w_gdocs_cu_hardening_run.py
- Test: tests/test_w_gdocs_cu_hardening_run.py
