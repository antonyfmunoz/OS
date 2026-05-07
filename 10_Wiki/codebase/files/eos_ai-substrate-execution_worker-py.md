---
type: codebase-file
path: eos_ai/substrate/execution_worker.py
module: eos_ai.substrate.execution_worker
lines: 361
size: 14153
generated: 2026-05-07
---

# eos_ai/substrate/execution_worker.py

Execution worker — scheduler handler that bridges requests to adapters.

Subscribes to ``execution_requested`` (and ``execution_retried``) events.
When an event arrives it deserializes the request, finds the adapter,
runs the primitive with a timeout, and emits exactly one result event.
...

**Lines:** 361 | **Size:** 14,153 bytes

## Depends On

- [[eos_ai-substrate-event_scheduler-py]]
- [[eos_ai-substrate-execution_adapter-py]]
- [[eos_ai-substrate-execution_contract-py]]
- [[eos_ai-substrate-execution_events-py]]

## Contains

- **class** [[eos_ai-substrate-execution_worker-py-ExecutionWorker]] — 4 methods
- **fn** [[eos_ai-substrate-execution_worker-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-execution_worker-py-_iso_now]]`() → str`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Optional
from eos_ai.substrate.event_scheduler import ExecutionResult as SchedulerExecutionResult
from eos_ai.substrate.event_scheduler import SchedulerEvent
from eos_ai.substrate.execution_adapter import ExecutionAdapter
from eos_ai.substrate.execution_contract import ExecutionRequest
from eos_ai.substrate.execution_contract import ExecutionResult
from eos_ai.substrate.execution_contract import ExecutionStatus
from eos_ai.substrate.execution_events import build_execution_completed_event
from eos_ai.substrate.execution_events import build_execution_failed_event
from eos_ai.substrate.execution_events import build_execution_rejected_event
from eos_ai.substrate.execution_events import build_execution_timed_out_event
from eos_ai.substrate.runtime_state_store import RuntimeStateStore
```
