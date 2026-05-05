# W0-001 Backend Completion Status Matrix

**Phase**: 96.2
**Date**: 2026-05-04
**Status**: ACTIVE
**Last updated by**: Phase 96.2 — MCP Backend Parity Classification

---

## Google Docs Extraction — Backend Completion Status

| Backend | Type | Independence | Status | Blocker |
|---------|------|:------------|:------:|---------|
| API tab-aware extractor | API | Reference | **COMPLETE** | None |
| CLI wrapper (wraps API) | CLI | LEVEL_0 | **COMPLETE** (interface) | Not independent fallback |
| CLI direct protocol | CLI | LEVEL_1 | NOT IMPLEMENTED | No standalone implementation exists |
| CLI vendor/native tool | CLI | LEVEL_2 | UNKNOWN | No tool evaluated |
| MCP wrapper around API extractor | MCP | LEVEL_0 | NOT IMPLEMENTED | Interface wrapper only |
| MCP API connector | MCP | LEVEL_1 | NOT IMPLEMENTED | Must prove tab-aware + canonical records |
| MCP vendor/tool wrapper | MCP | LEVEL_2 | UNKNOWN | No tool evaluated for all-tabs support |
| MCP local file/export connector | MCP | LEVEL_3 | NOT APPROVED | Requires export/local-file policy |
| MCP computer-use controller | MCP | LEVEL_4 | MAPS TO CU | Same as CU below |
| Computer Use (native/local GUI) | CU | LEVEL_4 | **PARTIAL_NEEDS_HARDENING** | Foreground ownership blocks clipboard |
| Browser automation (Playwright/CDP) | BA | varies | **BLOCKED** | Not approved unless separately approved |
| Local export/file parser | LOCAL_FILE | LEVEL_3 | NOT APPROVED | Requires export/download/sync approval |
| Manual/human fallback | MANUAL | LEVEL_5 | AVAILABLE | Not scalable |

## Summary

- **1 COMPLETE backend**: API (tab-aware)
- **1 COMPLETE interface wrapper**: CLI (not independent)
- **1 PARTIAL backend**: Computer Use (LEVEL_4, foreground blocked)
- **5 NOT IMPLEMENTED**: CLI direct, MCP wrapper, MCP API, MCP vendor, MCP local
- **1 BLOCKED**: Browser automation
- **1 NOT APPROVED**: Local export/file

## Independence Analysis

- LEVEL_0 backends (CLI wrapper, MCP wrapper): share same failure domain as API
- LEVEL_1 backends (CLI direct, MCP API connector): different implementation, same API dependency
- LEVEL_2 backends (CLI vendor, MCP vendor): different toolchain, possibly same API
- LEVEL_3 backends (MCP local file, local export): different data channel — survive API outage
- LEVEL_4 backends (Computer Use): different modality — most independent

## Memory Promotion Status

**Memory promotion is NOT allowed.**

Reason: Only one backend (API) is COMPLETE. CLI wrapper is LEVEL_0 (same failure domain).
No independent fallback has reached COMPLETE status.

Until at least one LEVEL_1+ backend reaches COMPLETE:
- Source records may be stored
- Memory promotion requires separate review
- Re-extraction after backend improvement may be required

## Next Gate

**REVIEW_BACKEND_PARITY_STATUS_FIRST**

Before any memory promotion:
1. Confirm API tab-aware extraction is validated for all W0-001 documents
2. Evaluate available MCP tools for Google Docs capability
3. Determine whether CU hardening or MCP API connector is the better next investment
