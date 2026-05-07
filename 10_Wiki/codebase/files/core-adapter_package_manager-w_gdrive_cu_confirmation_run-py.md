---
type: codebase-file
path: core/adapter_package_manager/w_gdrive_cu_confirmation_run.py
module: core.adapter_package_manager.w_gdrive_cu_confirmation_run
lines: 188
size: 7638
generated: 2026-05-07
---

# core/adapter_package_manager/w_gdrive_cu_confirmation_run.py

W-GDRIVE-CU-001 Confirmation Run.

Executes or prepares a Drive CU confirmation run to finalize
the provisional 100% maturity from Phase 96.7F.

...

**Lines:** 188 | **Size:** 7,638 bytes

## Contains

- **class** [[core-adapter_package_manager-w_gdrive_cu_confirmation_run-py-WDriveCUConfirmationStatus]] — 0 methods
- **class** [[core-adapter_package_manager-w_gdrive_cu_confirmation_run-py-WDriveCUConfirmationResult]] — 1 methods
- **fn** [[core-adapter_package_manager-w_gdrive_cu_confirmation_run-py-run_w_gdrive_cu_confirmation]]`(preflight, founder_confirmation) → WDriveCUConfirmationResult`
- **fn** [[core-adapter_package_manager-w_gdrive_cu_confirmation_run-py-evaluate_w_gdrive_cu_confirmation_result]]`(result) → bool`
- **fn** [[core-adapter_package_manager-w_gdrive_cu_confirmation_run-py-build_w_gdrive_cu_confirmation_report]]`(result) → dict[str, Any]`

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
from cu_proof_audit import CUProofAuditResult
from cu_proof_audit import audit_w_gdrive_cu_001_proof
```
