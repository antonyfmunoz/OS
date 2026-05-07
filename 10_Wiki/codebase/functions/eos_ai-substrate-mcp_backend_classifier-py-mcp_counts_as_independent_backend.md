---
type: codebase-function
file: eos_ai/substrate/mcp_backend_classifier.py
line: 168
generated: 2026-05-07
---

# mcp_counts_as_independent_backend

**File:** [[eos_ai-substrate-mcp_backend_classifier-py]] | **Line:** 168
**Signature:** `mcp_counts_as_independent_backend(profile) → bool`

Determine if an MCP tool counts as an independent backend.

## Calls

- [[eos_ai-substrate-extraction_backend_contracts-py-independence_counts_as_fallback]]
- [[eos_ai-substrate-mcp_backend_classifier-py-infer_independence_level]]

## Called By

- [[eos_ai-substrate-mcp_backend_classifier-py-build_mcp_backend_matrix_row]]
- [[eos_ai-substrate-mcp_backend_classifier-py-evaluate_mcp_against_extraction_contract]]
- [[eos_ai-substrate-mcp_backend_discovery-py-build_mcp_discovery_report]]
- [[eos_ai-substrate-mcp_backend_discovery-py-register_mcp_candidate_backend]]
