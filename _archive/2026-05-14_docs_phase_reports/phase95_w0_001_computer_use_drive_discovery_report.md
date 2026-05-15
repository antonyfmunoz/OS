# Phase 95.0 — W0-001 Computer-Use-Only Drive Discovery Report

**Phase**: 95.0
**Status**: COMPLETE
**Date**: 2026-05-04
**Work Order**: WO-LOCAL-PILOT-GDRIVE-GDOCS-001
**Author**: Developer Agent

---

## 1. Executive Summary

Phase 95.0 proves that UMH can inventory visible Google Drive contents
through the local computer/browser UI when APIs are unavailable.
Using Windows UI Automation via Task Scheduler /IT, the system navigated
Chrome's Drive page, read the accessibility tree, and extracted 26 of 29
files (89.7% recall) without any API calls, Playwright, CDP, screenshots,
or credential access.

## 2. Why API Inventory Did Not Satisfy the Computer-Use Test

The API inventory (Phase 94D.9) proved the system can read Drive metadata
programmatically. However, the founder's intent for W0-001 was specifically
to test the **worst-case fallback path**: can the system operate through
the visible desktop UI like a human operator?

This is a fundamentally different capability:
- API = server-to-server, structured, reliable, fast
- Computer-use = eyes-and-hands, visual, fallback, proves adaptability

Both are valuable. The API is production-preferred. Computer-use is the
emergency fallback that proves the system isn't helpless without API access.

## 3. Computer-Use-Only Constraints

| Constraint | Enforced |
|-----------|:---:|
| No Google Drive API | YES |
| No GWS CLI | YES |
| No Playwright | YES |
| No Chrome DevTools Protocol | YES |
| No browser cookies read | YES |
| No OAuth token access | YES |
| No Chrome Login Data | YES |
| No screenshots stored | YES |
| No document content read | YES |
| No Gmail | YES |
| No account switching | YES |
| No credential capture | YES |
| No memory promotion | YES |

## 4. Observation/Control Backend Used

```
Method: WINDOWS_UI_AUTOMATION
Execution: Task Scheduler /IT (interactive session)
Script: PowerShell with UIAutomationClient assembly
Chrome flag: --force-renderer-accessibility
Navigation: InvokePattern on "My Drive" tree item
Data extraction: DataItem.Name from accessibility tree
```

## 5. Execution Path

```
VPS SSH → schtasks /create (chrome.exe --profile-directory="Profile 5" --force-renderer-accessibility drive.google.com) /IT
VPS SSH → schtasks /run
VPS SSH → schtasks /delete (cleanup)
[wait for page load]
VPS SSH → scp (transfer PowerShell UI Automation script)
VPS SSH → schtasks /create (powershell.exe -File drive_ui_read.ps1) /IT
VPS SSH → schtasks /run
[wait for completion]
VPS SSH → type (read output file)
VPS → parse + compare against API baseline
```

## 6. Discovery Results

| Metric | Value |
|--------|-------|
| Total items discovered | 26 |
| Google Docs | 25 |
| Microsoft Word | 1 |
| Unique file names | 22 (+ 5 "Untitled document" variants) |
| Scrolling performed | No (single viewport) |
| End of list reached | No (3 files below fold) |
| Documents opened | 0 |

## 7. Key Technical Discoveries

1. **Chrome accessibility tree requires `--force-renderer-accessibility`** — without this flag, UIAutomation only sees the browser chrome (buttons, address bar), not page content.

2. **Task Scheduler /IT is essential** — UIAutomation from SSH cannot see interactive session windows (Session 0 isolation applies to COM objects too).

3. **Drive file rows are `ControlType.DataItem`** — each row's `.Name` property contains: `"FileName FileType Modified DateStr owner More actions (Alt+A)"`

4. **Navigation via InvokePattern works** — clicking "My Drive" in the tree caused Drive to navigate and load the full file list.

5. **Chrome window identification by title** — the Drive tab is "Home - Google Drive - Google Chrome" which includes the profile name "Antony (empyreanstudios.co)".

## 8. Comparison to API Baseline

| Metric | Value |
|--------|-------|
| API baseline | 29 files |
| CU discovered | 26 files |
| Matching | 22 unique names (+ untitled variants) |
| Missing from CU | 3 (below scroll fold) |
| Extra in CU | 0 |
| False positives | 0 |
| Recall | 89.7% |
| Precision | 100% |

Missing files: Antony Munoz Email Sequence, Script Storytelling Structures,
SEMAX: The Brain Upgrade Nobody Talks About — all sorted below the visible
viewport in alphabetical "My Drive" view.

## 9. Issues/Gaps

1. **Scroll not implemented** — would capture remaining 3 files
2. **Relative dates only** — UI shows "Mar 18" not "2026-03-18"
3. **No file IDs** — accessibility tree doesn't expose internal Google IDs
4. **"Untitled document" ambiguity** — 5 files with same name, only distinguishable by date
5. **Requires Chrome relaunch** — `--force-renderer-accessibility` is a launch flag
6. **Single-page proof** — not tested at scale (100+ files)

## 10. Code Created

| Module | Location |
|--------|----------|
| Local GUI control contracts | `eos_ai/substrate/local_gui_control_contracts.py` |
| Visible Drive UI inventory | `eos_ai/substrate/visible_drive_ui_inventory.py` |
| Drive UI inventory comparator | `eos_ai/substrate/drive_ui_inventory_comparator.py` |

## 11. Tests

| Test File | Count | Status |
|-----------|-------|--------|
| `test_phase95_local_gui_control_contracts.py` | 14 | PASSED |
| `test_phase95_visible_drive_ui_inventory.py` | 32 | PASSED |
| `test_phase95_drive_ui_inventory_comparator.py` | 11 | PASSED |
| **Total** | **57** | **ALL PASSED** |

## 12. Data Artifacts

| File | Purpose |
|------|---------|
| `data/drive_cu_inventory/visible_drive_inventory.json` | CU inventory result |
| `data/drive_discovery_inventory.json` | API baseline (from earlier phase) |

## 13. Hard Rules Compliance

- No API used for live discovery: YES
- No Playwright: YES
- No CDP: YES
- No Gmail: YES
- No account switching: YES
- No document opening: YES
- No document content reading: YES
- No credential/token capture: YES
- No screenshots stored: YES
- No memory promotion: YES
- No governance bypass: YES

## 14. Next Gate

**READY_FOR_COMPUTER_USE_DOCUMENT_SELECTION_OR_BACKEND_REPAIR**

Options:
- A: Scroll and re-inventory (capture remaining 3 files)
- B: Accept 89.7% recall as sufficient fallback proof
- C: Proceed to targeted document review gate
- D: Improve CU backend for production reliability
