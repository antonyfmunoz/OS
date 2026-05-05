# W0-001 Computer-Use Document Review Test Plan

**Date**: 2026-05-04
**Status**: PARTIALLY EXECUTED
**Sample Document**: UMH (8 tabs, 13,949 words)

---

## 1. Test Objectives

1. Open a Google Doc visibly in Chrome Profile 5
2. Detect document tabs through the visible UI / accessibility tree
3. Navigate between tabs using visible UI controls
4. Scroll through document content
5. Extract visible text through accessibility/UI observation
6. Compare CU extraction against tab-aware API extraction

## 2. Sample Selection

**Selected**: UMH (11p36P6TMvTnnz2KdQ2wYd3cDKfjHtCvVKp2_XEkuvz8)
- 8 document tabs
- 13,949 total words across all tabs
- Most recent strategic document
- Tests both tab detection and multi-page scrolling

## 3. Execution Results

### Step A: Open document in Chrome ✓
- Chrome launched with `--force-renderer-accessibility --profile-directory="Profile 5"`
- Document opened at `docs.google.com/document/d/.../edit`
- Window title: "UMH - Google Docs - Google Chrome"

### Step B: Detect document tabs ✓
- Method: `ControlType.TreeItem` in accessibility tree
- Tabs detected: 8
- Tab names: UNIVERSAL METS HARNESS, Tab 2, Tab 3, Tab 4, Tab 5, Tab 6, Tab 7, Tab 8
- Matches API: YES (8 tabs confirmed)

### Step C: Navigate between tabs — NOT ATTEMPTED
- Requires foreground ownership to invoke InvokePattern or click
- SetForegroundWindow failed (Windows limitation for cross-process input)

### Step D: Scroll through content — PARTIALLY EXECUTED
- SendKeys({PGDN}) sent but no content change detected
- Root cause: keystrokes not delivered to Chrome (foreground not owned)

### Step E: Extract visible text — FAILED
- Ctrl+A / Ctrl+C clipboard approach requires foreground
- TextPattern on Document element returns toolbar/menu text only
- Google Docs renders document content via canvas — not exposed as standard Text elements

### Step F: Compare CU vs API — NOT APPLICABLE
- No content extracted via CU for comparison

## 4. Technical Limitations Discovered

### Limitation 1: Windows Foreground Ownership
Task Scheduler /IT runs PowerShell in the user's interactive session,
but does NOT own the foreground. `SetForegroundWindow` fails because
Windows blocks foreground-stealing from non-foreground processes.

**Impact**: SendKeys, Ctrl+A, Ctrl+C all target the foreground window —
which is NOT the Chrome window since we can't steal foreground.

**Potential fixes**:
1. Launch Chrome FROM the same scheduled task (same process owns foreground)
2. Use `AttachThreadInput` to share foreground rights
3. Use `AppActivate` with delay after task launch
4. Use `FlagsEx` parameter in SetForegroundWindow

### Limitation 2: Google Docs Canvas Rendering
Google Docs doesn't use standard DOM text elements for document content.
The editor uses a canvas-like rendering approach where text is painted
into a container that UIAutomation can't parse into individual Text elements.

**Impact**: Even with foreground access, `ControlType.Text` elements only
capture toolbar/banner text, not document content.

**Potential fixes**:
1. Clipboard approach (Ctrl+A/C) — viable IF foreground is acquired
2. Google Docs accessibility mode (Ctrl+Alt+Z) may change rendering
3. Braille display mode may expose content differently

### Limitation 3: Tab Navigation
Google Docs tabs appear as TreeItem elements in the accessibility tree,
but invoking them requires either InvokePattern support or click coordinates.
InvokePattern may or may not be supported; clicks require foreground.

## 5. What WAS Proven

| Capability | Status |
|-----------|--------|
| Open document in correct Chrome profile | PROVEN |
| Detect document presence/title | PROVEN |
| Detect all document tabs by name | PROVEN |
| Count tabs accurately | PROVEN |
| Match tabs to API metadata | PROVEN |
| Read document text content | NOT PROVEN |
| Navigate between tabs | NOT PROVEN |
| Scroll through pages | NOT PROVEN |

## 6. Recommended Next Steps for CU Doc Reader Hardening

1. **Fix foreground ownership**: Launch Chrome + reader in SAME task
   so the scheduled task process owns the foreground.
2. **Test accessibility mode**: Try Ctrl+Alt+Z (screen reader mode)
   which may expose content as accessible text.
3. **Clipboard extraction**: Once foreground is fixed, Ctrl+A/C should
   work — Google Docs Ctrl+A selects all content in current tab.
4. **Tab navigation**: Use InvokePattern on TreeItem elements, or
   compute click coordinates from element BoundingRectangle.
