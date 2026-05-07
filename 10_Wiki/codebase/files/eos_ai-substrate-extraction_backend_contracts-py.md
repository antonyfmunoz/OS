---
type: codebase-file
path: eos_ai/substrate/extraction_backend_contracts.py
module: eos_ai.substrate.extraction_backend_contracts
lines: 268
size: 9848
generated: 2026-05-07
---

# eos_ai/substrate/extraction_backend_contracts.py

Extraction backend parity contracts for Phase 96.0 + 96.2.

Defines the canonical contract that ALL extraction backends (API, CLI,
MCP, Computer Use, Browser Automation, Local File) must satisfy.
No backend may claim COMPLETE unless it meets every coverage requirement.
...

**Lines:** 268 | **Size:** 9,848 bytes

## Used By

- [[eos_ai-substrate-canonical_source_record-py]]
- [[eos_ai-substrate-cu_document_reader_hardening_plan-py]]
- [[eos_ai-substrate-extraction_parity_comparator-py]]
- [[eos_ai-substrate-google_docs_backend_parity_matrix-py]]
- [[eos_ai-substrate-mcp_backend_classifier-py]]
- [[eos_ai-substrate-mcp_backend_contracts-py]]
- [[eos_ai-substrate-mcp_backend_discovery-py]]

## Contains

- **class** [[eos_ai-substrate-extraction_backend_contracts-py-ExtractionBackendType]] — 0 methods
- **class** [[eos_ai-substrate-extraction_backend_contracts-py-MCPSubtype]] — 0 methods
- **class** [[eos_ai-substrate-extraction_backend_contracts-py-BackendIndependenceLevel]] — 0 methods
- **class** [[eos_ai-substrate-extraction_backend_contracts-py-ExtractionCapability]] — 0 methods
- **class** [[eos_ai-substrate-extraction_backend_contracts-py-ExtractionCoverageStatus]] — 0 methods
- **class** [[eos_ai-substrate-extraction_backend_contracts-py-ExtractionFailureReason]] — 0 methods
- **class** [[eos_ai-substrate-extraction_backend_contracts-py-CapabilityDeclaration]] — 1 methods
- **class** [[eos_ai-substrate-extraction_backend_contracts-py-CanonicalExtractionContract]] — 1 methods
- **class** [[eos_ai-substrate-extraction_backend_contracts-py-BackendCapabilityReport]] — 1 methods
- **fn** [[eos_ai-substrate-extraction_backend_contracts-py-independence_counts_as_fallback]]`(level) → bool`
- **fn** [[eos_ai-substrate-extraction_backend_contracts-py-build_google_docs_contract]]`(file_id, backend_type) → CanonicalExtractionContract`
- **fn** [[eos_ai-substrate-extraction_backend_contracts-py-evaluate_backend_against_contract]]`(contract, capabilities, actual_backend_type) → BackendCapabilityReport`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
