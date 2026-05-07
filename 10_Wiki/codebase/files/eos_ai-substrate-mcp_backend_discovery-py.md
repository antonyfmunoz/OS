---
type: codebase-file
path: eos_ai/substrate/mcp_backend_discovery.py
module: eos_ai.substrate.mcp_backend_discovery
lines: 170
size: 6020
generated: 2026-05-07
---

# eos_ai/substrate/mcp_backend_discovery.py

MCP backend discovery for Phase 96.3.

Discovery/classification capability for MCP tools.
Does not connect to external MCP tools — creates the framework
for evaluating what should be assessed next.

**Lines:** 170 | **Size:** 6,020 bytes

## Depends On

- [[eos_ai-substrate-extraction_backend_contracts-py]]
- [[eos_ai-substrate-mcp_backend_classifier-py]]
- [[eos_ai-substrate-mcp_backend_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-mcp_backend_discovery-py-MCPDiscoveryPlan]] — 1 methods
- **class** [[eos_ai-substrate-mcp_backend_discovery-py-MCPDiscoveryReport]] — 1 methods
- **fn** [[eos_ai-substrate-mcp_backend_discovery-py-build_mcp_discovery_plan]]`(source_type) → MCPDiscoveryPlan`
- **fn** [[eos_ai-substrate-mcp_backend_discovery-py-parse_mcp_tool_manifest]]`(manifest) → MCPToolProfile`
- **fn** [[eos_ai-substrate-mcp_backend_discovery-py-classify_available_mcp_tool]]`(tool_manifest) → MCPToolProfile`
- **fn** [[eos_ai-substrate-mcp_backend_discovery-py-evaluate_mcp_tool_for_google_docs]]`(tool_profile) → dict[str, Any]`
- **fn** [[eos_ai-substrate-mcp_backend_discovery-py-register_mcp_candidate_backend]]`(tool_profile) → dict[str, Any]`
- **fn** [[eos_ai-substrate-mcp_backend_discovery-py-build_mcp_discovery_report]]`(tool_profiles) → MCPDiscoveryReport`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from eos_ai.substrate.extraction_backend_contracts import BackendIndependenceLevel
from eos_ai.substrate.extraction_backend_contracts import MCPSubtype
from eos_ai.substrate.mcp_backend_contracts import MCPToolProfile
from eos_ai.substrate.mcp_backend_classifier import classify_mcp_tool
from eos_ai.substrate.mcp_backend_classifier import evaluate_mcp_against_extraction_contract
from eos_ai.substrate.mcp_backend_classifier import mcp_counts_as_independent_backend
```
