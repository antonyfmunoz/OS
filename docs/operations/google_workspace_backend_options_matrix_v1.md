# Google Workspace Backend Options — Matrix v1
**Phase**: 96.3/96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04
---

## Core Rule
20 candidate backends exist for Google Workspace extraction. Each is classified by category, independence level, completeness status, and auth requirements. API COMPLETE is the reference standard. LEVEL_0 wrappers are not independent fallbacks.

## Details
### Backend Matrix

| #  | Backend                        | Category  | Independence | Status      | Auth Required           |
|----|--------------------------------|-----------|-------------|-------------|------------------------|
| 1  | Google Docs API (REST v1)      | API       | LEVEL_2     | COMPLETE    | OAuth2 / Service Acct  |
| 2  | Google Drive API (REST v3)     | API       | LEVEL_2     | COMPLETE    | OAuth2 / Service Acct  |
| 3  | Google Sheets API (REST v4)    | API       | LEVEL_2     | COMPLETE    | OAuth2 / Service Acct  |
| 4  | Google Apps Script             | SDK       | LEVEL_2     | PARTIAL     | Google Account         |
| 5  | gcloud CLI                     | CLI       | LEVEL_0     | COMPLETE    | OAuth2 (gcloud auth)   |
| 6  | gdocs-export CLI wrapper       | CLI       | LEVEL_0     | COMPLETE    | Inherits gcloud auth   |
| 7  | Python google-api-python-client| SDK       | LEVEL_1     | COMPLETE    | OAuth2 / Service Acct  |
| 8  | Node googleapis                | SDK       | LEVEL_1     | COMPLETE    | OAuth2 / Service Acct  |
| 9  | MCP gdocs server (API-based)   | MCP       | LEVEL_0     | PARTIAL     | OAuth2 passthrough     |
| 10 | MCP gdrive server              | MCP       | LEVEL_0     | PARTIAL     | OAuth2 passthrough     |
| 11 | Anthropic Computer Use         | CU        | LEVEL_2     | PARTIAL     | Browser Profile        |
| 12 | Playwright browser automation  | BROWSER   | LEVEL_1     | BLOCKED     | Browser Profile        |
| 13 | Puppeteer browser automation   | BROWSER   | LEVEL_1     | BLOCKED     | Browser Profile        |
| 14 | Selenium browser automation    | BROWSER   | LEVEL_1     | BLOCKED     | Browser Profile        |
| 15 | PyAutoGUI screen automation    | RPA       | LEVEL_1     | BLOCKED     | Local session          |
| 16 | Google Drive webhook           | WEBHOOK   | LEVEL_1     | CANDIDATE   | OAuth2 + push endpoint |
| 17 | Chrome extension (custom)      | EXTENSION | LEVEL_1     | CANDIDATE   | Chrome profile         |
| 18 | Google Takeout export          | EXPORT    | LEVEL_2     | CANDIDATE   | Google Account         |
| 19 | Drive sync (rclone)            | SYNC      | LEVEL_1     | CANDIDATE   | OAuth2                 |
| 20 | Hybrid API+CU fallback chain   | HYBRID    | LEVEL_2     | CANDIDATE   | Both OAuth2 + Profile  |

### Status Definitions
- **COMPLETE** — fully functional, tested against extraction contract
- **PARTIAL** — functional but missing fields or tab awareness
- **BLOCKED** — not approved for use (browser automation default)
- **CANDIDATE** — identified but not yet evaluated or tested

### Key Findings
- API backends (#1-3) are the reference standard — all others measured against them
- CLI wrappers (#5-6) are LEVEL_0 — they call the API, not independent extraction
- MCP servers (#9-10) are LEVEL_0 — they wrap the API, adding MCP transport only
- CU (#11) is genuinely independent (screen-based) but PARTIAL on coverage
- Browser automation (#12-14) is BLOCKED by default policy
- Webhook (#16) is event-driven, not extraction — different use case

## Constraints
- LEVEL_0 backends MUST NOT count toward fallback chain diversity
- BLOCKED backends require explicit founder approval before any use
- CANDIDATE backends require full 10-step discovery before use
- All backends MUST produce output conforming to CanonicalSourceRecord
- CU backend MUST have tab-aware scrolling for Google Docs multi-tab documents

## Phase 96.6 Update — Tool Mastery Status

Each backend option now tracks a `tool_mastery_status` field indicating whether the access path has been evaluated against the Google Docs Tool Mastery Pack.

| # | Backend | Tool Mastery Status |
|---|---------|-------------------|
| 1 | Google Docs API (REST v1) | **REQUIRED** — must pass `google_docs_mastery_pack` checks |
| 2 | Google Drive API (REST v3) | **REQUIRED** — must pass `google_docs_mastery_pack` checks |
| 3 | Google Sheets API (REST v4) | NOT_ASSESSED — separate mastery pack needed |
| 4 | Google Apps Script | NOT_ASSESSED |
| 5 | gcloud CLI | **REQUIRED** — wraps API, must verify `includeTabsContent` passthrough |
| 6 | gdocs-export CLI wrapper | **REQUIRED** — wraps API, must verify tab support |
| 7 | Python google-api-python-client | **REQUIRED** — SDK must pass `google_docs_mastery_pack` checks |
| 8 | Node googleapis | **REQUIRED** — SDK must pass `google_docs_mastery_pack` checks |
| 9 | MCP gdocs server (API-based) | **REQUIRED** — must verify underlying API call includes tab support |
| 10 | MCP gdrive server | **REQUIRED** — must verify tab-aware extraction |
| 11 | Anthropic Computer Use | **REQUIRED** — must discover and navigate tabs via screen |
| 12-14 | Browser automation | REQUIRED_IF_APPROVED — mastery needed if founder approves |
| 15-20 | Other | NOT_ASSESSED |

Access paths marked REQUIRED must demonstrate mastery-level completeness before promotion. An access path that connects successfully but ignores tabs is not mature.

## References
- `docs/operations/backend_registry_selection_doctrine_v1.md` — selection factors
- `docs/operations/mcp_backend_discovery_policy_v1.md` — MCP evaluation
- `docs/operations/google_docs_all_tabs_extraction_contract_v1.md` — tab extraction
- `docs/operations/computer_use_full_document_reader_requirements_v1.md` — CU requirements
- `docs/operations/google_docs_tool_mastery_pack_v1.md` — mastery pack reference
- `docs/operations/tool_mastery_pack_doctrine_v1.md` — mastery requirements
