---
type: codebase-file
path: eos_ai/substrate/mcp_backend_contracts.py
module: eos_ai.substrate.mcp_backend_contracts
lines: 87
size: 3113
generated: 2026-05-07
---

# eos_ai/substrate/mcp_backend_contracts.py

MCP backend contracts for Phase 96.2.

MCP is a protocol/adapter layer, not automatically an independent backend.
An MCP server/tool must be classified by its underlying capability and
failure domain before it can be evaluated against the extraction contract.
...

**Lines:** 87 | **Size:** 3,113 bytes

## Depends On

- [[eos_ai-substrate-extraction_backend_contracts-py]]

## Used By

- [[eos_ai-substrate-mcp_backend_classifier-py]]
- [[eos_ai-substrate-mcp_backend_discovery-py]]

## Contains

- **class** [[eos_ai-substrate-mcp_backend_contracts-py-MCPToolProfile]] — 1 methods
- **class** [[eos_ai-substrate-mcp_backend_contracts-py-MCPBackendEvaluation]] — 1 methods

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from eos_ai.substrate.extraction_backend_contracts import BackendIndependenceLevel
from eos_ai.substrate.extraction_backend_contracts import ExtractionBackendType
from eos_ai.substrate.extraction_backend_contracts import ExtractionCoverageStatus
from eos_ai.substrate.extraction_backend_contracts import MCPSubtype
```
