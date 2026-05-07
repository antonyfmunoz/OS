---
type: codebase-file
path: core/adapter_package_manager/w_gdrive_cu_rerun_result.py
module: core.adapter_package_manager.w_gdrive_cu_rerun_result
lines: 209
size: 7813
generated: 2026-05-07
---

# core/adapter_package_manager/w_gdrive_cu_rerun_result.py

W-GDRIVE-CU-001 Rerun Result Contract.

Defines the result structure for a Drive CU rerun while founder is
present. Evaluates whether the rerun proof is sufficient to finalize
Drive CU at 100%.
...

**Lines:** 209 | **Size:** 7,813 bytes

## Contains

- **class** [[core-adapter_package_manager-w_gdrive_cu_rerun_result-py-WDriveCURerunStatus]] — 0 methods
- **class** [[core-adapter_package_manager-w_gdrive_cu_rerun_result-py-WDriveCURerunResult]] — 1 methods
- **fn** [[core-adapter_package_manager-w_gdrive_cu_rerun_result-py-build_w_gdrive_cu_rerun_result]]`(founder_present, founder_confirmed, chrome_opened, drive_loaded, correct_account, correct_profile, inventory_captured, item_count, api_parity, method_cu_only, governance_clean) → WDriveCURerunResult`
- **fn** [[core-adapter_package_manager-w_gdrive_cu_rerun_result-py-evaluate_w_gdrive_cu_rerun_result]]`(result) → WDriveCURerunResult`
- **fn** [[core-adapter_package_manager-w_gdrive_cu_rerun_result-py-rerun_result_finalizes_drive_cu]]`(result) → bool`
- **fn** [[core-adapter_package_manager-w_gdrive_cu_rerun_result-py-summarize_w_gdrive_cu_rerun_result]]`(result) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
