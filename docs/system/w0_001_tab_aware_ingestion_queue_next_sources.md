# W0-001 Tab-Aware Ingestion Queue — Next Sources

**Date**: 2026-05-04
**Status**: COMPLETE

---

## 1. Current Corpus Status

| Source | Status | Words |
|--------|--------|------:|
| 28 Google Docs (My Drive) | COMPLETE (tab-aware) | 283,831 |
| 1 Word Doc (LYFEOS_Product_Development_Roadmap.docx) | NOT EXTRACTED | unknown |
| Shared With Me docs | NOT INVENTORIED | unknown |

## 2. Next Sources (Priority Order)

### Priority 1: Word Document
- **LYFEOS_Product_Development_Roadmap.docx** (file ID: 1svTpbCtrmSoxFlCKau7doOU2PGr4hP-m)
- Already in Drive inventory
- Requires separate extraction method (different mime type)
- Likely contains LyfeOS roadmap content that may overlap with LyfeOS Google Doc
- **Action**: Approve Word doc export/read, or convert to Google Doc format

### Priority 2: Shared With Me
- Documents shared by others may contain relevant business context
- Requires separate Drive API query (not yet executed)
- **Action**: Run `gws drive files list` with `sharedWithMe=true` filter

### Priority 3: Google Sheets
- No sheets currently in My Drive
- If any exist in Shared With Me, they may contain data (financials, leads, metrics)
- **Action**: Inventory after Shared With Me scan

### Priority 4: External Sources
- Notion databases (if any — NOTION_MORNING_BRIEF_ID exists but points to dead DB)
- Slack/Discord history (if relevant to business context)
- Email (Gmail access is BLOCKED by policy)

## 3. Blocked Sources

| Source | Reason |
|--------|--------|
| Gmail | Policy: no Gmail access |
| Third-party SaaS data | Requires separate connectors |
| Browser history/bookmarks | Not in scope |
| Local files (Windows) | Requires CU or file share |

## 4. Recommendation

1. Extract the Word doc (requires approval for download/export OR Google Docs conversion)
2. Scan Shared With Me for additional documents
3. Everything else can wait until after memory promotion review
