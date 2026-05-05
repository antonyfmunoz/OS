# W0-001 Computer Use Document Reader Hardening Plan

**Date**: 2026-05-04
**Status**: PLAN DEFINED — NOT YET EXECUTING
**Goal**: Harden CU backend until it can extract the same canonical source records as API

---

## 1. Current CU Backend State

| Capability | Status | Blocker |
|-----------|--------|---------|
| Drive file inventory | COMPLETE | — |
| Doc tab detection | COMPLETE (8/8) | — |
| Doc title detection | COMPLETE | — |
| Doc tab navigation | BLOCKED | Foreground ownership |
| Doc body extraction | BLOCKED | Foreground + canvas rendering |
| Doc scrolling | BLOCKED | Foreground ownership |
| Clipboard capture | BLOCKED | Foreground ownership |
| Full canonical record | BLOCKED | All content capabilities blocked |

## 2. Root Cause

Windows does not allow a non-foreground process to steal foreground.
Task Scheduler /IT runs in the user's interactive session but is NOT the foreground window.
Chrome retains foreground. SendKeys/clipboard target the foreground — wrong window.

## 3. Hardening Phases

### Phase A: Fix Foreground Ownership

**Goal**: Achieve reliable foreground control of Chrome window.

Options to evaluate (requires approval before install):

| Option | Method | Risk | Approval Required |
|--------|--------|------|:-:|
| A1 | Launch Chrome FROM the same scheduled task process | Low | No (restructure only) |
| A2 | UIAutomation SetFocus on specific element by process ID | Low | No |
| A3 | PowerShell `[Win32]::SetForegroundWindow` with `AttachThreadInput` | Medium | No |
| A4 | AutoHotkey window activation script | Low | Yes (install) |
| A5 | Local desktop daemon (always-foreground worker) | Medium | Yes (new service) |
| A6 | Manual founder foreground confirmation | None | No (degraded UX) |

**Recommended**: A1 first (zero-install, restructure task to launch Chrome + reader as single process).
If A1 fails, try A3 (AttachThreadInput is a Windows API, no install needed).

### Phase B: Clipboard Content Extraction

**Prerequisite**: Phase A (foreground ownership solved).

Steps:
1. Bring Chrome/Doc window to foreground (Phase A)
2. Click inside document body area (coordinates from BoundingRectangle)
3. Ctrl+A (select all text in current tab)
4. Ctrl+C (copy to clipboard)
5. Read clipboard via PowerShell `Get-Clipboard`
6. Validate: clipboard content is document text (not toolbar text)
7. Clear clipboard after capture (security hygiene)

**Success criteria**: Clipboard contains document body text matching API reference.

### Phase C: Tab Navigation

**Prerequisite**: Phase A (foreground for click delivery).

Steps:
1. Detect tab TreeItem elements via UIAutomation
2. Get BoundingRectangle for each tab
3. Click center of tab element (or use InvokePattern)
4. Wait for accessibility tree to update (tab switch confirmation)
5. Verify: new tab title matches clicked tab
6. Repeat for all tabs

**Success criteria**: All tabs navigated, each tab switch confirmed.

### Phase D: Scroll-and-Read

**Prerequisite**: Phase B (clipboard works) + Phase C (tabs navigable).

Steps:
1. Navigate to tab
2. Ctrl+A / Ctrl+C — capture initial content
3. If document is long (word count suggests multi-page):
   - PgDn / scroll
   - Re-capture via Ctrl+A/C
   - Compare: if same content, end of tab reached
   - If new content, accumulate
4. Detect end-of-tab: no new content after scroll

Note: Google Docs Ctrl+A selects ALL content in the current tab regardless of
scroll position. This means scroll-and-read may not be needed if Ctrl+A captures
the full tab in one shot. Validate this hypothesis in Phase B.

### Phase E: Full Parity Validation

**Prerequisite**: Phases A-D all working.

Steps:
1. Select a multi-tab document (UMH: 8 tabs, 13,949 words)
2. Run full CU extraction: launch → detect tabs → navigate each → extract each
3. Emit CanonicalSourceRecord from CU extraction
4. Compare against API canonical record using parity comparator
5. Measure: tab recall, word recall, phrase recall
6. Target: 95%+ word recall for MVP, 99%+ for production

## 4. Governance Rules

| Rule | Enforcement |
|------|-------------|
| Clipboard only from approved document body | Policy check: URL must be docs.google.com |
| No clipboard from login/password pages | URL validation before extraction |
| No API/CLI calls during CU extraction | Backend type enforcement |
| No screenshot storage | Blocked by policy |
| No credential capture | Blocked by policy |
| Stop on unexpected account switch | Account verification before each doc |
| Clear clipboard after use | Explicit step in extraction flow |

## 5. Implementation Priority

This is Track B — not blocking on Track A (API re-extraction).
Implementation should proceed only after:
1. Track A re-extraction is accepted ✓ (done)
2. Founder approves foreground fix method
3. Hardening phases executed sequentially (A → B → C → D → E)

## 6. Exit Criteria

CU document reader hardening is COMPLETE when:
- [ ] Phase A: foreground ownership reliably acquired
- [ ] Phase B: clipboard captures full tab body text
- [ ] Phase C: all tabs navigable
- [ ] Phase D: multi-page tabs fully captured (or Ctrl+A proves sufficient)
- [ ] Phase E: parity comparator shows 95%+ word recall vs API
- [ ] CU backend status upgrades from PARTIAL to COMPLETE in parity matrix
