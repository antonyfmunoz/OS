---
type: codebase-file
path: eos_ai/substrate/mcp_backend_classifier.py
module: eos_ai.substrate.mcp_backend_classifier
lines: 191
size: 7637
generated: 2026-05-07
---

# eos_ai/substrate/mcp_backend_classifier.py

MCP backend classifier for Phase 96.2.

Classifies MCP tools by their underlying capability and failure domain,
determines independence level, and evaluates against the canonical
extraction contract.
...

**Lines:** 191 | **Size:** 7,637 bytes

## Depends On

- [[eos_ai-substrate-extraction_backend_contracts-py]]
- [[eos_ai-substrate-mcp_backend_contracts-py]]

## Used By

- [[eos_ai-substrate-mcp_backend_discovery-py]]

## Contains

- **fn** [[eos_ai-substrate-mcp_backend_classifier-py-infer_mcp_subtype]]`(profile) → MCPSubtype`
- **fn** [[eos_ai-substrate-mcp_backend_classifier-py-infer_independence_level]]`(profile) → BackendIndependenceLevel`
- **fn** [[eos_ai-substrate-mcp_backend_classifier-py-classify_mcp_tool]]`(profile) → MCPToolProfile`
- **fn** [[eos_ai-substrate-mcp_backend_classifier-py-evaluate_mcp_against_extraction_contract]]`(profile, contract) → MCPBackendEvaluation`
- **fn** [[eos_ai-substrate-mcp_backend_classifier-py-mcp_counts_as_independent_backend]]`(profile) → bool`
- **fn** [[eos_ai-substrate-mcp_backend_classifier-py-build_mcp_backend_matrix_row]]`(profile) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from eos_ai.substrate.extraction_backend_contracts import BackendIndependenceLevel
from eos_ai.substrate.extraction_backend_contracts import CanonicalExtractionContract
from eos_ai.substrate.extraction_backend_contracts import ExtractionBackendType
from eos_ai.substrate.extraction_backend_contracts import ExtractionCoverageStatus
from eos_ai.substrate.extraction_backend_contracts import MCPSubtype
from eos_ai.substrate.extraction_backend_contracts import independence_counts_as_fallback
from eos_ai.substrate.mcp_backend_contracts import MCPBackendEvaluation
from eos_ai.substrate.mcp_backend_contracts import MCPToolProfile
```
