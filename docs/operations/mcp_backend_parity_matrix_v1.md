# MCP Backend Parity Matrix v1

**Phase**: 96.2
**Date**: 2026-05-04
**Status**: ACTIVE

---

## Google Docs Backend Matrix (Full — Including MCP)

| # | Backend | Independence | Status | Notes |
|---|---------|:------------|:------:|-------|
| 1 | API tab-aware extractor | N/A (reference) | COMPLETE | Tab-aware re-extraction done |
| 2 | CLI wrapper around API | LEVEL_0 | COMPLETE (interface only) | Wraps same API extractor |
| 3 | CLI direct protocol | LEVEL_1 | NOT IMPLEMENTED | Would call documents.get includeTabsContent=true directly |
| 4 | CLI vendor/native tool | LEVEL_2 | UNKNOWN | Must prove all-tabs support |
| 5 | MCP wrapper around API extractor | LEVEL_0 | NOT IMPLEMENTED | Interface wrapper only — not independent |
| 6 | MCP API connector | LEVEL_1 | NOT IMPLEMENTED | Must be tab-aware and canonical-record compliant |
| 7 | MCP vendor/tool wrapper | LEVEL_2 | UNKNOWN | Not proven all-tabs compliant |
| 8 | MCP local file/export connector | LEVEL_3 | NOT APPROVED | Requires export/local-file policy |
| 9 | MCP computer-use controller | LEVEL_4 | MAPS TO CU | Same capabilities and blockers |
| 10 | Computer Use native/local GUI | LEVEL_4 | PARTIAL_NEEDS_HARDENING | Foreground blocker active |
| 11 | Browser automation | depends | BLOCKED | Not approved — Playwright/CDP/Selenium |
| 12 | Local export/file parser | LEVEL_3 | NOT APPROVED | Requires export/download/sync approval |

## Key Observations

1. **API is the only COMPLETE backend** — all others are partial, unknown, or not implemented
2. **CLI wrapper shares the same failure domain** as API (LEVEL_0)
3. **MCP wrapper would also be LEVEL_0** — not a new fallback
4. **MCP API connector is possible** at LEVEL_1 but not yet implemented
5. **Computer Use is the only LEVEL_4 backend** but is blocked by foreground ownership
6. **Browser automation is policy-blocked** across all interfaces

## Parity Rules

- No backend can claim COMPLETE unless it satisfies the full extraction contract
- LEVEL_0 backends do not count as independent fallback
- MCP and CLI are not automatically independent because they are "different interfaces"
- Same API dependency = same failure domain, regardless of protocol layer

## Implementation

Defined in: `eos_ai/substrate/google_docs_backend_parity_matrix.py`
