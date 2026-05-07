---
type: codebase-file
path: eos_ai/substrate/execution_result_handler.py
module: eos_ai.substrate.execution_result_handler
lines: 499
size: 18543
generated: 2026-05-07
---

# eos_ai/substrate/execution_result_handler.py

Control-plane handler that processes execution results.

Subscribes to execution_completed, execution_failed, execution_timed_out,
and execution_rejected events. Validates, deduplicates, writes outputs to
state, and emits lifecycle follow-up events.
...

**Lines:** 499 | **Size:** 18,543 bytes

## Depends On

- [[eos_ai-substrate-event_scheduler-py]]
- [[eos_ai-substrate-execution_contract-py]]
- [[eos_ai-substrate-execution_events-py]]

## Contains

- **class** [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler]] — 10 methods
- **fn** [[eos_ai-substrate-execution_result_handler-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-execution_result_handler-py-_utcnow]]`() → str`

## Import Statements

```python
from __future__ import annotations
import sys
from datetime import datetime
from datetime import timezone
from typing import Any
from eos_ai.substrate.execution_contract import ExecutionClass
from eos_ai.substrate.execution_contract import ExecutionRequest
from eos_ai.substrate.execution_contract import ExecutionResult
from eos_ai.substrate.execution_contract import ExecutionStatus
from eos_ai.substrate.execution_events import build_execution_retried_event
from eos_ai.substrate.event_scheduler import ExecutionResult as SchedulerExecutionResult
from eos_ai.substrate.event_scheduler import SchedulerEvent
from eos_ai.substrate.runtime_state_store import RuntimeStateStore
```
