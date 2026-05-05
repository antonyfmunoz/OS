# W0-001 Computer-Use Fallback Test Plan v1

**Phase**: 95.0
**Work Order**: WO-LOCAL-PILOT-GDRIVE-GDOCS-001
**Date**: 2026-05-04

---

## 1. Objective

Prove that UMH can inventory visible Google Drive contents through the
local computer/browser UI when APIs/connectors are unavailable.

## 2. Prerequisites

- Chrome Profile 5 active with antonyfm@empyreanstudios.co
- Chrome launched with `--force-renderer-accessibility`
- Windows UI Automation available on local PC
- Task Scheduler /IT path working
- Google Drive open in My Drive view

## 3. Execution Steps

1. Launch Chrome Profile 5 with Drive URL and accessibility flag
2. Wait for page load
3. Execute PowerShell UI Automation script via Task Scheduler /IT
4. Script navigates to "My Drive" via accessibility tree
5. Script reads all DataItem elements (file rows)
6. Script outputs file names, types, dates to text file
7. VPS retrieves output file
8. VPS parses into structured inventory
9. VPS compares against API baseline

## 4. Success Criteria

- [x] Worker operates through visible Chrome UI only
- [x] Worker produces computer-use-derived inventory
- [x] Worker does NOT use API/CLI/Playwright/CDP
- [x] Worker stops before opening any document
- [x] Worker compares against API baseline
- [x] Worker reports discrepancies
- [x] Worker emits next gate

## 5. Results

- Items discovered: 26 (of 29 in API baseline)
- Recall: 89.7%
- Missing: 3 files (below scroll fold)
- Method: Windows UI Automation
- Chrome flag: --force-renderer-accessibility
- Scrolling: not performed (single page view)
- Documents opened: 0
