---
type: codebase-file
path: core/adapter_package_manager/local_worker_cu_preflight.py
module: core.adapter_package_manager.local_worker_cu_preflight
lines: 177
size: 6161
generated: 2026-05-07
---

# core/adapter_package_manager/local_worker_cu_preflight.py

Local Worker CU Preflight.

Evaluates whether the local worker is available and capable of
running Computer Use tasks for W0-001. Runs from the VPS orchestrator
node — detects when the local Windows worker is unreachable.
...

**Lines:** 177 | **Size:** 6,161 bytes

## Contains

- **class** [[core-adapter_package_manager-local_worker_cu_preflight-py-LocalWorkerCUPreflightStatus]] — 0 methods
- **class** [[core-adapter_package_manager-local_worker_cu_preflight-py-LocalWorkerCUPreflightResult]] — 1 methods
- **fn** [[core-adapter_package_manager-local_worker_cu_preflight-py-run_local_worker_cu_preflight]]`(force_host, force_gui, force_worker, governance_safe, founder_presence_confirmed) → LocalWorkerCUPreflightResult`
- **fn** [[core-adapter_package_manager-local_worker_cu_preflight-py-local_worker_preflight_blocks_drive_cu]]`(result) → bool`
- **fn** [[core-adapter_package_manager-local_worker_cu_preflight-py-local_worker_preflight_blocks_docs_cu]]`(result) → bool`
- **fn** [[core-adapter_package_manager-local_worker_cu_preflight-py-summarize_local_worker_preflight]]`(result) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import os
import platform
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
