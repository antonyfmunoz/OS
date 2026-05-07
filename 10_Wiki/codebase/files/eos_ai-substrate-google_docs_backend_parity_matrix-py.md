---
type: codebase-file
path: eos_ai/substrate/google_docs_backend_parity_matrix.py
module: eos_ai.substrate.google_docs_backend_parity_matrix
lines: 400
size: 15124
generated: 2026-05-07
---

# eos_ai/substrate/google_docs_backend_parity_matrix.py

Google Docs backend parity matrix for Phase 96.0 + 96.2.

Evaluates API, CLI, MCP, and Computer Use backends against the canonical
Google Docs extraction contract and produces a capability matrix.

...

**Lines:** 400 | **Size:** 15,124 bytes

## Depends On

- [[eos_ai-substrate-extraction_backend_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-google_docs_backend_parity_matrix-py-BackendMatrixEntry]] — 1 methods
- **class** [[eos_ai-substrate-google_docs_backend_parity_matrix-py-GoogleDocsParityMatrix]] — 1 methods
- **fn** [[eos_ai-substrate-google_docs_backend_parity_matrix-py-mark_api_capabilities]]`(tab_aware) → list[CapabilityDeclaration]`
- **fn** [[eos_ai-substrate-google_docs_backend_parity_matrix-py-mark_cli_capabilities]]`(wraps_tab_aware_api) → list[CapabilityDeclaration]`
- **fn** [[eos_ai-substrate-google_docs_backend_parity_matrix-py-mark_computer_use_capabilities]]`() → list[CapabilityDeclaration]`
- **fn** [[eos_ai-substrate-google_docs_backend_parity_matrix-py-build_google_docs_backend_matrix]]`(file_id, api_tab_aware, cli_wraps_api) → GoogleDocsParityMatrix`
- **fn** [[eos_ai-substrate-google_docs_backend_parity_matrix-py-_report_to_matrix_entry]]`(report) → BackendMatrixEntry`
- **fn** [[eos_ai-substrate-google_docs_backend_parity_matrix-py-_build_mcp_matrix_entries]]`() → list[BackendMatrixEntry]`
- **fn** [[eos_ai-substrate-google_docs_backend_parity_matrix-py-_build_browser_automation_entry]]`() → BackendMatrixEntry`
- **fn** [[eos_ai-substrate-google_docs_backend_parity_matrix-py-_build_local_file_entry]]`() → BackendMatrixEntry`
- **fn** [[eos_ai-substrate-google_docs_backend_parity_matrix-py-recommend_next_backend_hardening_step]]`(api_report, cli_report, cu_report) → str`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from eos_ai.substrate.extraction_backend_contracts import BackendCapabilityReport
from eos_ai.substrate.extraction_backend_contracts import BackendIndependenceLevel
from eos_ai.substrate.extraction_backend_contracts import CanonicalExtractionContract
from eos_ai.substrate.extraction_backend_contracts import CapabilityDeclaration
from eos_ai.substrate.extraction_backend_contracts import ExtractionBackendType
from eos_ai.substrate.extraction_backend_contracts import ExtractionCapability
from eos_ai.substrate.extraction_backend_contracts import ExtractionCoverageStatus
from eos_ai.substrate.extraction_backend_contracts import ExtractionFailureReason
from eos_ai.substrate.extraction_backend_contracts import MCPSubtype
from eos_ai.substrate.extraction_backend_contracts import build_google_docs_contract
from eos_ai.substrate.extraction_backend_contracts import evaluate_backend_against_contract
```
