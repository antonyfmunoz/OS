---
type: codebase-file
path: core/adapter_package_manager/local_worker_dispatch_check.py
module: core.adapter_package_manager.local_worker_dispatch_check
lines: 221
size: 8152
generated: 2026-05-07
---

# core/adapter_package_manager/local_worker_dispatch_check.py

Local Worker Dispatch Check.

Evaluates whether the VPS can dispatch a CU rerun packet to the local
Windows worker. Checks SSH reachability, station directory state, and
local inbox availability. Produces manual fallback instructions when
...

**Lines:** 221 | **Size:** 8,152 bytes

## Contains

- **class** [[core-adapter_package_manager-local_worker_dispatch_check-py-LocalWorkerDispatchStatus]] — 0 methods
- **class** [[core-adapter_package_manager-local_worker_dispatch_check-py-LocalWorkerDispatchCheck]] — 1 methods
- **fn** [[core-adapter_package_manager-local_worker_dispatch_check-py-check_local_worker_dispatch_readiness]]`(force_station_dir, force_inbox, force_outbox, force_ssh_key, force_packet) → LocalWorkerDispatchCheck`
- **fn** [[core-adapter_package_manager-local_worker_dispatch_check-py-build_w0_001_cu_dispatch_packet]]`() → dict[str, Any]`
- **fn** [[core-adapter_package_manager-local_worker_dispatch_check-py-local_worker_dispatch_blocks_run]]`(check) → bool`
- **fn** [[core-adapter_package_manager-local_worker_dispatch_check-py-summarize_dispatch_check]]`(check) → dict[str, Any]`
- **fn** [[core-adapter_package_manager-local_worker_dispatch_check-py-_build_manual_instructions]]`() → list[str]`

## Import Statements

```python
from __future__ import annotations
import json
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Any
```
