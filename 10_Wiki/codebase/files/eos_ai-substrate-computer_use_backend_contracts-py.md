---
type: codebase-file
path: eos_ai/substrate/computer_use_backend_contracts.py
module: eos_ai.substrate.computer_use_backend_contracts
lines: 152
size: 5861
generated: 2026-05-07
---

# eos_ai/substrate/computer_use_backend_contracts.py

Computer-use backend contracts for Phase 94D.3.

Additive-only module. Defines backend classes for local execution,
selection policy, and the explicit approval requirement for browser
automation fallback.
...

**Lines:** 152 | **Size:** 5,861 bytes

## Depends On

- [[eos_ai-substrate-work_order_contracts-py]]

## Used By

- [[eos_ai-substrate-local_worker_relay_packets-py]]

## Contains

- **class** [[eos_ai-substrate-computer_use_backend_contracts-py-ComputerUseBackend]] — 0 methods
- **class** [[eos_ai-substrate-computer_use_backend_contracts-py-BackendSelectionReason]] — 0 methods
- **class** [[eos_ai-substrate-computer_use_backend_contracts-py-BackendPolicy]] — 2 methods
- **fn** [[eos_ai-substrate-computer_use_backend_contracts-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-computer_use_backend_contracts-py-select_backend]]`(task_type, work_order_id) → BackendPolicy`
- **fn** [[eos_ai-substrate-computer_use_backend_contracts-py-requires_approval_for_browser_automation]]`(policy) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from eos_ai.substrate.work_order_contracts import WorkOrderTaskType
```
