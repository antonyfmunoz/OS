---
type: codebase-file
path: core/adapter_package_manager/google_cu_parity_validator.py
module: core.adapter_package_manager.google_cu_parity_validator
lines: 164
size: 5273
generated: 2026-05-07
---

# core/adapter_package_manager/google_cu_parity_validator.py

CU Parity Validator.

Validates Computer Use extraction results against API baselines
for Drive inventory and Docs tab-aware extraction.

...

**Lines:** 164 | **Size:** 5,273 bytes

## Contains

- **class** [[core-adapter_package_manager-google_cu_parity_validator-py-CUParityValidationResult]] — 1 methods
- **fn** [[core-adapter_package_manager-google_cu_parity_validator-py-build_w0_001_api_baseline]]`() → dict[str, Any]`
- **fn** [[core-adapter_package_manager-google_cu_parity_validator-py-validate_drive_cu_against_api]]`(cu_file_count, api_file_count, provenance_match) → CUParityValidationResult`
- **fn** [[core-adapter_package_manager-google_cu_parity_validator-py-validate_docs_cu_against_api]]`(actual_docs, actual_tabs, actual_child_tabs, actual_words, provenance_match) → CUParityValidationResult`
- **fn** [[core-adapter_package_manager-google_cu_parity_validator-py-cu_parity_blocks_maturity]]`(result) → bool`
- **fn** [[core-adapter_package_manager-google_cu_parity_validator-py-summarize_cu_parity]]`(result) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
