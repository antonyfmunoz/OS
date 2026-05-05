# Phase 96.2 — MCP Backend Parity Classification Report

**Date**: 2026-05-04
**Status**: COMPLETE

---

## 1. Founder Correction

The founder clarified that MCP should be included in the backend/access-path
matrix when available. However, the correction included a critical distinction:

**MCP is NOT automatically a backend by itself.**

MCP is a tool protocol / adapter layer. An MCP server's actual underlying
capability determines what backend class it belongs to.

## 2. MCP Classification Doctrine

MCP tools must be classified by what they actually do:

| MCP Subtype | What It Does | Independence Level |
|-------------|-------------|:------------------:|
| MCP_AS_INTERFACE | Wraps same internal extractor | LEVEL_0 (NOT independent) |
| MCP_API_CONNECTOR | Calls official provider API | LEVEL_1 |
| MCP_VENDOR_TOOL_WRAPPER | Wraps vendor CLI/tool | LEVEL_2 |
| MCP_LOCAL_FILE_CONNECTOR | Reads local/synced/exported files | LEVEL_3 |
| MCP_COMPUTER_USE_CONTROLLER | Controls desktop/browser/accessibility | LEVEL_4 |
| MCP_BROWSER_AUTOMATION | Controls browser via CDP/Playwright | Classified but BLOCKED |
| MCP_NATIVE_SOURCE_CONNECTOR | Own source-specific connector | LEVEL_3+ |
| MCP_UNKNOWN | Not yet inspected | LEVEL_0 (conservative default) |

## 3. Why MCP Is Not Automatically a Backend

Because "MCP" describes the protocol, not the data access channel:
- An MCP tool that proxies calls to the same Python API extractor adds zero
  fallback value — same code, same failure domain, same API dependency
- An MCP tool that reads locally synced files adds genuine independence
- The protocol layer is irrelevant to backend independence; the underlying
  data access channel is what matters

## 4. MCP Subtype Matrix

See `docs/operations/mcp_backend_classification_doctrine_v1.md` for full
subtype definitions and classification rules.

## 5. Independence Levels

See `docs/operations/mcp_tool_independence_levels_v1.md` for the 6-level
independence framework. Key rule: LEVEL_0 never counts as fallback.

## 6. Google Docs MCP Requirements

See `docs/operations/google_docs_mcp_backend_requirements_v1.md` for the
12 requirements an MCP Google Docs backend must satisfy to claim COMPLETE.

## 7. Updated Backend Matrix

| Backend | Independence | Status |
|---------|:------------|:------:|
| API tab-aware | Reference | COMPLETE |
| CLI wrapper | LEVEL_0 | COMPLETE (interface) |
| CLI direct | LEVEL_1 | NOT IMPLEMENTED |
| CLI vendor | LEVEL_2 | UNKNOWN |
| MCP wrapper | LEVEL_0 | NOT IMPLEMENTED |
| MCP API connector | LEVEL_1 | NOT IMPLEMENTED |
| MCP vendor wrapper | LEVEL_2 | UNKNOWN |
| MCP local file | LEVEL_3 | NOT APPROVED |
| MCP CU controller | LEVEL_4 | MAPS TO CU |
| Computer Use | LEVEL_4 | PARTIAL_NEEDS_HARDENING |
| Browser automation | varies | BLOCKED |
| Local export | LEVEL_3 | NOT APPROVED |

## 8. Current Status for W0-001

- API extraction: **COMPLETE** — tab-aware re-extraction done
- CLI: **COMPLETE** as interface wrapper (LEVEL_0, not independent)
- MCP: **NOT IMPLEMENTED** — no MCP tools currently deployed for Google Docs extraction
- Computer Use: **PARTIAL_NEEDS_HARDENING** — foreground ownership blocks clipboard

## 9. Memory Promotion

**Memory promotion is NOT allowed.**

Only one backend (API) is COMPLETE. The CLI wrapper is LEVEL_0 (same failure
domain). No independent fallback has reached COMPLETE status.

## 10. Next Recommended Gate

**REVIEW_BACKEND_PARITY_STATUS_FIRST**

Before any further action:
1. Confirm API tab-aware extraction is validated for all W0-001 documents
2. Evaluate available MCP tools for Google Docs capability
3. Determine whether CU hardening or MCP API connector is the better
   next investment for backend diversity

## Code Artifacts Created/Updated

### New files:
- `eos_ai/substrate/mcp_backend_contracts.py` — MCPToolProfile, MCPBackendEvaluation
- `eos_ai/substrate/mcp_backend_classifier.py` — classify, infer, evaluate, build_row
- `tests/test_phase962_mcp_backend_contracts.py` — 12 tests
- `tests/test_phase962_mcp_backend_classifier.py` — 13 tests
- `tests/test_phase962_mcp_backend_parity_matrix.py` — 9 tests
- `docs/operations/mcp_backend_classification_doctrine_v1.md`
- `docs/operations/mcp_backend_parity_matrix_v1.md`
- `docs/operations/mcp_tool_independence_levels_v1.md`
- `docs/operations/google_docs_mcp_backend_requirements_v1.md`
- `docs/system/w0_001_backend_completion_status_matrix.md`
- `docs/system/phase962_mcp_backend_parity_update_report.md`

### Updated files:
- `eos_ai/substrate/extraction_backend_contracts.py` — added MCP, LOCAL_FILE backend types; MCPSubtype enum; BackendIndependenceLevel enum
- `eos_ai/substrate/google_docs_backend_parity_matrix.py` — added MCP entries, browser automation entry, local file entry to matrix

### Also fixed (pre-existing):
- `eos_ai/substrate/__init__.py` — resolved merge conflict
- `eos_ai/substrate/nodes.py` — resolved merge conflict
- `eos_ai/substrate/session_discord_bridge.py` — resolved merge conflict
- `eos_ai/substrate/session_watcher.py` — resolved merge conflict

## Test Results

- Phase 96.0 existing tests: **41 passed**
- Phase 96.2 new tests: **34 passed**
- Total: **75 passed, 0 failed**
