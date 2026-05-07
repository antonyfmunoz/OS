---
type: codebase-file
path: core/adapter_package_manager/google_cu_execution_probe.py
module: core.adapter_package_manager.google_cu_execution_probe
lines: 196
size: 6420
generated: 2026-05-07
---

# core/adapter_package_manager/google_cu_execution_probe.py

CU Execution Probe.

Evaluates whether the current runtime environment can execute
Computer Use hardening or production parity tests.

...

**Lines:** 196 | **Size:** 6,420 bytes

## Contains

- **class** [[core-adapter_package_manager-google_cu_execution_probe-py-CUExecutionProbeStatus]] — 0 methods
- **class** [[core-adapter_package_manager-google_cu_execution_probe-py-CUExecutionProbeResult]] — 1 methods
- **fn** [[core-adapter_package_manager-google_cu_execution_probe-py-build_cu_probe_result]]`(probe_id, target_package_id, source_system, browser_profile, account_expected, account_confirmed, visible_session_available, drive_visible, doc_visible, ui_access_available, extraction_available, governance_safe) → CUExecutionProbeResult`
- **fn** [[core-adapter_package_manager-google_cu_execution_probe-py-cu_probe_allows_hardening]]`(result) → bool`
- **fn** [[core-adapter_package_manager-google_cu_execution_probe-py-cu_probe_allows_production_parity]]`(result) → bool`
- **fn** [[core-adapter_package_manager-google_cu_execution_probe-py-cu_probe_blocks_maturity]]`(result) → bool`
- **fn** [[core-adapter_package_manager-google_cu_execution_probe-py-summarize_cu_probe]]`(result) → dict[str, Any]`
- **fn** [[core-adapter_package_manager-google_cu_execution_probe-py-build_vps_environment_probe]]`(target_package_id) → CUExecutionProbeResult`
- **fn** [[core-adapter_package_manager-google_cu_execution_probe-py-build_windows_local_probe]]`(target_package_id, account_confirmed, drive_visible, doc_visible, extraction_available) → CUExecutionProbeResult`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
