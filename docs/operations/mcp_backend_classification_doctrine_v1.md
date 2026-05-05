# MCP Backend Classification Doctrine v1

**Phase**: 96.2
**Date**: 2026-05-04
**Status**: ACTIVE

---

## Core Doctrine

MCP is a protocol/adapter layer, not automatically an independent backend.

An MCP server or tool must be classified by its underlying capability
and failure domain before it can claim any backend status.

"MCP" alone tells you nothing about what access channel the tool uses,
what data source it reads, or whether it survives the same failures as
an existing backend.

## The Seven MCP Classes

### 1. MCP_AS_INTERFACE (LEVEL_0)
The MCP tool calls the same internal extractor already used elsewhere.

- Useful interface — convenient way to access existing capability
- NOT independent — same implementation, same failure domain
- Cannot serve as fallback
- Example: An MCP server that proxies calls to the existing Python
  Google Docs API extractor

### 2. MCP_API_CONNECTOR (LEVEL_1)
The MCP tool connects to the source through official provider APIs.

- Different implementation from internal extractor
- Still depends on the same provider API
- Can be contract-compliant if tab-aware
- Example: Google Drive/Docs MCP using Google APIs directly

### 3. MCP_VENDOR_TOOL_WRAPPER (LEVEL_2)
The MCP tool wraps a vendor CLI/tool/service.

- Distinct operational/toolchain path
- May still depend on provider APIs underneath
- Example: MCP wrapping GAM, rclone, or similar vendor tools

### 4. MCP_LOCAL_FILE_CONNECTOR (LEVEL_3)
The MCP tool reads local synced/exported/archive files.

- Different data access channel entirely
- Requires export/download/sync approval
- Survives API outages
- Example: MCP reading Google Takeout exports or locally synced files

### 5. MCP_COMPUTER_USE_CONTROLLER (LEVEL_4)
The MCP tool controls desktop/browser/mouse/keyboard/accessibility.

- This IS Computer Use exposed through MCP
- Maps to the Computer Use backend directly
- Same capabilities and same blockers as CU
- Example: MCP server that drives the accessibility tree

### 6. MCP_BROWSER_AUTOMATION (classified but blocked)
The MCP tool controls browser automation (Playwright/CDP/Selenium).

- Must be separately approved if blocked by policy
- Not automatically available
- Example: Playwright MCP server

### 7. MCP_NATIVE_SOURCE_CONNECTOR (LEVEL_3+)
The MCP tool has its own source-specific connector and produces
full canonical records.

- Counts as a real backend IF it satisfies the extraction contract
- Must prove tab traversal, body extraction, provenance
- Example: A purpose-built Google Docs connector MCP

## Independence Levels

| Level | Name | Counts as Fallback? |
|-------|------|:------------------:|
| LEVEL_0 | Interface Wrapper | NO |
| LEVEL_1 | Different Implementation, Same Provider API | YES (limited) |
| LEVEL_2 | Different Toolchain, Same Provider API | YES |
| LEVEL_3 | Different Data Access Channel | YES |
| LEVEL_4 | Different Modality | YES |
| LEVEL_5 | Human Assisted | YES |

## The Independence Rule

MCP counts as an independent backend ONLY when it provides distinct:
- Implementation, OR
- Access channel, OR
- Runtime, OR
- Toolchain, OR
- Failure-domain value

A wrapper around the same internal extractor is LEVEL_0 and does NOT count.

## Why This Matters

Without this classification, the system could:
1. Count an MCP wrapper as a "second backend" when it shares the exact
   same code and failure domain as the API backend
2. Claim redundancy where none exists
3. Miss that a local-file MCP connector actually IS independent

The classification prevents false independence claims while correctly
recognizing genuine access diversity.

## Implementation

- Enum definitions: `eos_ai/substrate/extraction_backend_contracts.py`
- MCP contracts: `eos_ai/substrate/mcp_backend_contracts.py`
- MCP classifier: `eos_ai/substrate/mcp_backend_classifier.py`
- Backend matrix: `eos_ai/substrate/google_docs_backend_parity_matrix.py`
