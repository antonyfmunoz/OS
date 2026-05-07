---
type: codebase-file
path: eos_ai/substrate/cu_document_reader_hardening_plan.py
module: eos_ai.substrate.cu_document_reader_hardening_plan
lines: 257
size: 9740
generated: 2026-05-07
---

# eos_ai/substrate/cu_document_reader_hardening_plan.py

Computer Use document reader hardening plan for W0-001.

Defines the phased approach to bring the CU backend to parity with API
for Google Docs extraction. Each phase has prerequisites, steps, and
exit criteria.
...

**Lines:** 257 | **Size:** 9,740 bytes

## Depends On

- [[eos_ai-substrate-extraction_backend_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-cu_document_reader_hardening_plan-py-HardeningPhase]] — 0 methods
- **class** [[eos_ai-substrate-cu_document_reader_hardening_plan-py-PhaseStatus]] — 0 methods
- **class** [[eos_ai-substrate-cu_document_reader_hardening_plan-py-ForegroundFixOption]] — 0 methods
- **class** [[eos_ai-substrate-cu_document_reader_hardening_plan-py-HardeningPhaseSpec]] — 1 methods
- **class** [[eos_ai-substrate-cu_document_reader_hardening_plan-py-CUHardeningPlan]] — 3 methods
- **fn** [[eos_ai-substrate-cu_document_reader_hardening_plan-py-build_hardening_plan]]`() → CUHardeningPlan`
- **fn** [[eos_ai-substrate-cu_document_reader_hardening_plan-py-evaluate_foreground_fix_options]]`() → list[dict[str, Any]]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from eos_ai.substrate.extraction_backend_contracts import ExtractionBackendType
from eos_ai.substrate.extraction_backend_contracts import ExtractionCapability
from eos_ai.substrate.extraction_backend_contracts import ExtractionCoverageStatus
from eos_ai.substrate.extraction_backend_contracts import ExtractionFailureReason
```
