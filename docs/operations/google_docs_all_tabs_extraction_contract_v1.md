# Google Docs All-Tabs Extraction Contract v1

**Phase**: 96.0
**Date**: 2026-05-04
**Status**: ACTIVE

---

## Contract

A Google Doc is NOT fully extracted unless ALL of the following are true:

1. The document is inventoried (file_id, title, mime_type known).
2. Every top-level tab is discovered.
3. Every child tab is discovered recursively.
4. Every tab body is extracted.
5. Empty tabs are marked as `is_empty=True`.
6. Hidden/inaccessible tabs are marked with reason.
7. Text is attributed to the correct tab (tab_id + tab_path).
8. Tab order/hierarchy is preserved (tab_order, parent_tab_id, depth).
9. Document-level metadata is preserved (title, dates, owner).
10. Backend type is recorded in provenance.

## API Implementation

```
gws docs documents get --params '{"documentId": "<ID>", "includeTabsContent": true}'
```

Requirements:
- `includeTabsContent=true` MUST be set
- Traverse `document.tabs` (NOT `document.body`)
- Recursively traverse `childTabs` at every level
- Extract text from each `tab.documentTab.body`
- Preserve: `tabProperties.tabId`, `tabProperties.title`
- Record depth/hierarchy via parent tracking

Response structure:
```json
{
  "tabs": [
    {
      "tabProperties": { "tabId": "...", "title": "..." },
      "documentTab": { "body": { "content": [...] } },
      "childTabs": [ ... recursive ... ]
    }
  ]
}
```

## CLI Implementation

Requirements:
- Either use a CLI command that exposes all tabs
- Or call the same tab-aware extraction under CLI wrapper
- Must pass `includeTabsContent=true` parameter
- Must normalize output to CanonicalSourceRecord
- Backend type must be recorded as CLI even if underlying call is API

Example:
```bash
gws docs documents get --params '{"documentId": "<ID>", "includeTabsContent": true}'
```

## Computer Use Implementation

Requirements:
- Open the document visibly in Chrome/Profile 5
- Detect the tabs UI via accessibility tree
- Enumerate ALL visible document tabs
- Navigate each tab (click or InvokePattern)
- Extract visible/body text per tab
- Scroll through each tab if needed
- Use accessibility tree / UI Automation / clipboard capture only if approved
- Do NOT use API/CLI/Playwright/CDP for live extraction
- Emit the same CanonicalSourceRecord schema

Allowed techniques:
- Windows UI Automation / accessibility tree reading
- Keyboard navigation (Tab, Enter, Arrow keys)
- Mouse navigation (click at coordinates)
- Scrolling (PgDn, wheel)
- Clipboard capture from selected document text (Ctrl+A/C)

Blocked:
- API calls
- CLI calls
- Playwright
- CDP
- Downloads/exports
- Screenshot storage (unless separately approved)

## Known Current State

| Backend | Tab Discovery | Tab Navigation | Content Extraction |
|---------|:------------:|:--------------:|:-----------------:|
| API | COMPLETE | N/A | COMPLETE |
| CLI | COMPLETE (wraps API) | N/A | COMPLETE |
| Computer Use | PARTIAL (detection proven) | BLOCKED | BLOCKED |

## Computer Use Blockers

1. **Foreground Ownership**: SetForegroundWindow fails for Task Scheduler /IT.
   Fix: launch Chrome from same task process.
2. **Canvas Rendering**: Google Docs doesn't expose body text as standard
   accessibility Text elements. Fix: clipboard capture after foreground fix.
3. **Tab Navigation**: TreeItem InvokePattern not tested. Fix: depends on
   foreground ownership fix.
