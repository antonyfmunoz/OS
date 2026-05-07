---
type: codebase-file
path: eos_ai/substrate/work_order_dispatch.py
module: eos_ai.substrate.work_order_dispatch
lines: 246
size: 7378
generated: 2026-05-07
---

# eos_ai/substrate/work_order_dispatch.py

Work order dispatch preparation for Phase 94R.

Additive-only module. Prepares dispatch packages and assesses readiness
without calling network, sending to bridge, or executing local actions.

...

**Lines:** 246 | **Size:** 7,378 bytes

## Depends On

- [[eos_ai-substrate-work_order_contracts-py]]
- [[eos_ai-substrate-work_order_factory-py]]

## Contains

- **class** [[eos_ai-substrate-work_order_dispatch-py-DispatchReadiness]] — 0 methods
- **class** [[eos_ai-substrate-work_order_dispatch-py-ReadinessCheck]] — 0 methods
- **class** [[eos_ai-substrate-work_order_dispatch-py-DispatchPackage]] — 1 methods
- **fn** [[eos_ai-substrate-work_order_dispatch-py-check_vps_file_readiness]]`() → list[ReadinessCheck]`
- **fn** [[eos_ai-substrate-work_order_dispatch-py-check_contract_readiness]]`() → list[ReadinessCheck]`
- **fn** [[eos_ai-substrate-work_order_dispatch-py-check_local_healthcheck_status]]`(local_healthcheck_passed) → list[ReadinessCheck]`
- **fn** [[eos_ai-substrate-work_order_dispatch-py-assess_readiness]]`(checks) → DispatchReadiness`
- **fn** [[eos_ai-substrate-work_order_dispatch-py-build_dispatch_package]]`(local_healthcheck_passed) → DispatchPackage`
- **fn** [[eos_ai-substrate-work_order_dispatch-py-save_dispatch_package]]`(package, directory) → Path`

## Import Statements

```python
from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path
from eos_ai.substrate.work_order_contracts import UNIVERSAL_BLOCKED_ACTIONS
from eos_ai.substrate.work_order_contracts import WorkOrder
from eos_ai.substrate.work_order_contracts import WorkOrderStatus
from eos_ai.substrate.work_order_factory import create_google_workspace_discovery_work_order
from eos_ai.substrate.work_order_factory import validate_work_order
from eos_ai.substrate.work_order_factory import work_order_to_bridge_payload
```
