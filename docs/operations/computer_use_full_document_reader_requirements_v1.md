# Computer Use Full Document Reader Requirements v1

**Phase**: 96.0
**Date**: 2026-05-04
**Status**: REQUIREMENTS DEFINED — NOT YET IMPLEMENTED

---

## Goal

Computer Use must eventually produce the same `DocumentSourceRecord`
as the API backend for any Google Doc, using only visible UI interaction.

## Required Capabilities (in order)

1. Launch correct Chrome profile (Profile 5).
2. Open target Google Doc by URL.
3. Confirm correct account (check toolbar/avatar).
4. Detect document title (from window title or accessibility tree).
5. Detect all document tabs (ControlType.TreeItem elements).
6. Navigate every tab (click or InvokePattern).
7. Extract all visible body text per tab.
8. Scroll through long documents/tabs to capture all content.
9. Detect end of document/tab (no new content after scroll).
10. Preserve per-tab provenance (which tab, method used, scroll count).
11. Avoid edit mode mutations (read-only observation).
12. Avoid changing document content.
13. Avoid screenshots unless separately approved.
14. Avoid credential capture.
15. Stop if account/login changes unexpectedly.

## Allowed Extraction Techniques

| Technique | Approval Status | Notes |
|-----------|:--------------:|-------|
| Windows UI Automation / accessibility tree | APPROVED | Primary observation method |
| Keyboard navigation (Tab, Enter, arrows) | APPROVED | For tab navigation, scrolling |
| Mouse navigation (click at coordinates) | APPROVED | For tab clicks, focus |
| Scrolling (PgDn, mouse wheel) | APPROVED | For multi-page content |
| Clipboard capture (Ctrl+A/C on document body) | APPROVED with policy | See clipboard policy below |
| Temporary observation buffers | APPROVED | In-memory only, not persisted to disk |

## Blocked Techniques (unless separately approved)

| Technique | Status | Reason |
|-----------|--------|--------|
| API calls | BLOCKED | Defeats CU-only constraint |
| CLI calls | BLOCKED | Defeats CU-only constraint |
| Playwright | BLOCKED | Not visible UI interaction |
| Chrome DevTools Protocol (CDP) | BLOCKED | Not visible UI interaction |
| Screenshots as stored artifacts | BLOCKED | Privacy/storage concern |
| Download/export | BLOCKED | Modifies document state |

## Clipboard Capture Policy

Clipboard capture IS computer use when performed through visible UI:
1. Target document must be the approved document (not login/account page).
2. Clipboard contents are treated as source text — not secret capture.
3. Only allowed when the active document is the approved target.
4. BLOCKED on login pages, password fields, account settings.
5. Clipboard is cleared after extraction (security hygiene).
6. Content goes directly into `TabSourceRecord.text_content`.

## Current Blockers

| Blocker | Root Cause | Fix Path |
|---------|-----------|----------|
| Foreground ownership | Task Scheduler /IT doesn't own foreground | Launch Chrome from same scheduled task |
| Canvas rendering | Google Docs doesn't expose body as Text elements | Use clipboard (Ctrl+A/C) after foreground fix |
| Tab navigation | InvokePattern/click requires foreground | Fix foreground first |

## Implementation Phases

### Phase A: Fix Foreground Ownership
- Create a single scheduled task that launches Chrome AND runs reader
- Same process owns foreground → SendKeys/clipboard work
- Verify: SetForegroundWindow returns True

### Phase B: Clipboard Content Extraction
- With foreground fixed: Ctrl+A → Ctrl+C → read clipboard
- Verify: clipboard contains document text (not toolbar text)
- Measure: word count vs API reference

### Phase C: Tab Navigation
- Click on TreeItem tab elements OR use InvokePattern
- Verify: tab switch detected (accessibility tree changes)
- Iterate all tabs: navigate → extract → next

### Phase D: Scroll-and-Read
- For tabs too long for single clipboard capture
- PgDn → re-capture → deduplicate → accumulate
- Detect end-of-content (no new text after scroll)

### Phase E: Full Parity Validation
- Extract all tabs of a multi-tab document
- Compare against API record using parity comparator
- Target: 95%+ text recall for MVP, 99%+ for production

## Success Criteria

Computer Use backend passes parity validation when:
- Tab discovery: 100% match with API
- Tab navigation: all tabs successfully opened
- Text extraction: >= 95% word recall vs API reference
- False positives: < 1% (no toolbar/menu text in output)
- Provenance: all fields populated correctly
- Coverage status: COMPLETE (not PARTIAL or BLOCKED)
