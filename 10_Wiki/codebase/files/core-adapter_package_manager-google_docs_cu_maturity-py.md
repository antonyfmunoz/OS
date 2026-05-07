---
type: codebase-file
path: core/adapter_package_manager/google_docs_cu_maturity.py
module: core.adapter_package_manager.google_docs_cu_maturity
lines: 349
size: 11674
generated: 2026-05-07
---

# core/adapter_package_manager/google_docs_cu_maturity.py

Google Docs CU Maturity Gate (W-GDOCS-CU-001).

Evaluates whether the Docs Computer Use path has reached 100%
maturity based on proof of execution and parity validation.

...

**Lines:** 349 | **Size:** 11,674 bytes

## Contains

- **class** [[core-adapter_package_manager-google_docs_cu_maturity-py-DocsCUProof]] — 1 methods
- **class** [[core-adapter_package_manager-google_docs_cu_maturity-py-GoogleDocsCUMaturityDecision]] — 1 methods
- **fn** [[core-adapter_package_manager-google_docs_cu_maturity-py-_build_phase_w0_001r_proof]]`() → DocsCUProof`
- **fn** [[core-adapter_package_manager-google_docs_cu_maturity-py-evaluate_w_gdocs_cu_001_maturity]]`(proof, has_tool_mastery, has_tests) → GoogleDocsCUMaturityDecision`
- **fn** [[core-adapter_package_manager-google_docs_cu_maturity-py-w_gdocs_cu_001_is_100_percent_mature]]`(proof) → bool`
- **fn** [[core-adapter_package_manager-google_docs_cu_maturity-py-build_w_gdocs_cu_001_gap_report]]`(proof) → dict[str, Any]`
- **fn** [[core-adapter_package_manager-google_docs_cu_maturity-py-build_w_gdocs_cu_001_hardening_work_orders]]`(proof) → list[str]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
