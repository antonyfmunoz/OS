---
type: codebase-file
path: eos_ai/substrate/work_order_contracts.py
module: eos_ai.substrate.work_order_contracts
lines: 286
size: 10788
generated: 2026-05-07
---

# eos_ai/substrate/work_order_contracts.py

Work order contracts for Phase 93R.1.

Additive-only module. Does not import from or modify any existing
substrate module (actions.py, station.py, station_bus.py, control_commands.py).
These types sit alongside SafeAction and ControlCommand — they do not replace them.

**Lines:** 286 | **Size:** 10,788 bytes

## Used By

- [[eos_ai-substrate-computer_use_backend_contracts-py]]
- [[eos_ai-substrate-work_order_dispatch-py]]
- [[eos_ai-substrate-work_order_factory-py]]
- [[eos_ai-substrate-worker_node_runtime-py]]

## Contains

- **class** [[eos_ai-substrate-work_order_contracts-py-WorkOrderStatus]] — 0 methods
- **class** [[eos_ai-substrate-work_order_contracts-py-WorkOrderTaskType]] — 0 methods
- **class** [[eos_ai-substrate-work_order_contracts-py-AuthorityMode]] — 0 methods
- **class** [[eos_ai-substrate-work_order_contracts-py-SensitivityLevel]] — 0 methods
- **class** [[eos_ai-substrate-work_order_contracts-py-WorkOrder]] — 4 methods
- **class** [[eos_ai-substrate-work_order_contracts-py-WorkOrderResult]] — 2 methods
- **fn** [[eos_ai-substrate-work_order_contracts-py-_generate_work_order_id]]`() → str`
- **fn** [[eos_ai-substrate-work_order_contracts-py-_now_iso]]`() → str`

## Import Statements

```python
from __future__ import annotations
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
```
