---
type: codebase-file
path: core/adapter_package_manager/w_gdocs_cu_hardening_run.py
module: core.adapter_package_manager.w_gdocs_cu_hardening_run
lines: 213
size: 8484
generated: 2026-05-07
---

# core/adapter_package_manager/w_gdocs_cu_hardening_run.py

W-GDOCS-CU-001 Hardening Run.

Executes or prepares a Docs CU hardening run to advance toward
100% maturity. Docs CU has 7 gaps from Phase W0-001R.

...

**Lines:** 213 | **Size:** 8,484 bytes

## Contains

- **class** [[core-adapter_package_manager-w_gdocs_cu_hardening_run-py-WDocsCUHardeningStatus]] — 0 methods
- **class** [[core-adapter_package_manager-w_gdocs_cu_hardening_run-py-WDocsCUHardeningResult]] — 1 methods
- **fn** [[core-adapter_package_manager-w_gdocs_cu_hardening_run-py-run_w_gdocs_cu_hardening]]`(preflight, founder_confirmation) → WDocsCUHardeningResult`
- **fn** [[core-adapter_package_manager-w_gdocs_cu_hardening_run-py-evaluate_w_gdocs_cu_hardening_result]]`(result) → bool`
- **fn** [[core-adapter_package_manager-w_gdocs_cu_hardening_run-py-build_w_gdocs_cu_hardening_report]]`(result) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from local_worker_cu_preflight import LocalWorkerCUPreflightResult
from local_worker_cu_preflight import LocalWorkerCUPreflightStatus
from local_worker_cu_preflight import run_local_worker_cu_preflight
from cu_founder_confirmation_gate import FounderConfirmationStatus
from google_docs_cu_maturity import evaluate_w_gdocs_cu_001_maturity
```
