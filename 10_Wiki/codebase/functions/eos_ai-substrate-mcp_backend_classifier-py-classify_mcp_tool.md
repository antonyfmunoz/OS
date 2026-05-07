---
type: codebase-function
file: eos_ai/substrate/mcp_backend_classifier.py
line: 95
generated: 2026-05-07
---

# classify_mcp_tool

**File:** [[eos_ai-substrate-mcp_backend_classifier-py]] | **Line:** 95
**Signature:** `classify_mcp_tool(profile) → MCPToolProfile`

Classify an MCP tool by inferring subtype and independence level.

## Calls

- [[eos_ai-substrate-mcp_backend_classifier-py-infer_independence_level]]
- [[eos_ai-substrate-mcp_backend_classifier-py-infer_mcp_subtype]]

## Called By

- [[eos_ai-substrate-mcp_backend_classifier-py-build_mcp_backend_matrix_row]]
- [[eos_ai-substrate-mcp_backend_discovery-py-build_mcp_discovery_report]]
- [[eos_ai-substrate-mcp_backend_discovery-py-classify_available_mcp_tool]]
- [[eos_ai-substrate-mcp_backend_discovery-py-register_mcp_candidate_backend]]
