---
type: codebase-file
path: core/adapter_package_manager/w0_001_cu_slice_readiness.py
module: core.adapter_package_manager.w0_001_cu_slice_readiness
lines: 133
size: 4746
generated: 2026-05-07
---

# core/adapter_package_manager/w0_001_cu_slice_readiness.py

W0-001 CU Slice Readiness.

Evaluates combined Drive CU + Docs CU readiness for the W0-001
triple-test. CU slice is READY only when both packages are 100%.

...

**Lines:** 133 | **Size:** 4,746 bytes

## Contains

- **class** [[core-adapter_package_manager-w0_001_cu_slice_readiness-py-W0001CUSliceStatus]] — 0 methods
- **class** [[core-adapter_package_manager-w0_001_cu_slice_readiness-py-W0001CUSliceReadiness]] — 1 methods
- **fn** [[core-adapter_package_manager-w0_001_cu_slice_readiness-py-evaluate_w0_001_cu_slice_readiness]]`(drive_decision, docs_decision) → W0001CUSliceReadiness`
- **fn** [[core-adapter_package_manager-w0_001_cu_slice_readiness-py-w0_001_cu_slice_blocks_full_triple_test]]`(readiness) → bool`
- **fn** [[core-adapter_package_manager-w0_001_cu_slice_readiness-py-summarize_w0_001_cu_slice_readiness]]`(readiness) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from google_drive_cu_maturity import GoogleDriveCUMaturityDecision
from google_drive_cu_maturity import evaluate_w_gdrive_cu_001_maturity
from google_docs_cu_maturity import GoogleDocsCUMaturityDecision
from google_docs_cu_maturity import evaluate_w_gdocs_cu_001_maturity
```
