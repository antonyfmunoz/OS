---
type: codebase-file
path: eos_ai/substrate/execution_events.py
module: eos_ai.substrate.execution_events
lines: 168
size: 5003
generated: 2026-05-07
---

# eos_ai/substrate/execution_events.py

Event construction helpers for the execution fabric.

Thin builders that produce correctly-typed SchedulerEvents for every
execution lifecycle transition. Centralising construction here prevents
payload-schema drift across the worker, authority, and result handler.
...

**Lines:** 168 | **Size:** 5,003 bytes

## Depends On

- [[eos_ai-substrate-event_scheduler-py]]
- [[eos_ai-substrate-execution_contract-py]]

## Used By

- [[eos_ai-substrate-execution_authority-py]]
- [[eos_ai-substrate-execution_result_handler-py]]
- [[eos_ai-substrate-execution_worker-py]]

## Contains

- **fn** [[eos_ai-substrate-execution_events-py-build_execution_requested_event]]`(request, session_name, run_id) → SchedulerEvent`
- **fn** [[eos_ai-substrate-execution_events-py-build_execution_completed_event]]`(result, request_event_id, session_name, run_id) → SchedulerEvent`
- **fn** [[eos_ai-substrate-execution_events-py-build_execution_failed_event]]`(result, request_event_id, session_name, failure_reason, run_id) → SchedulerEvent`
- **fn** [[eos_ai-substrate-execution_events-py-build_execution_timed_out_event]]`(result, request_event_id, session_name, run_id) → SchedulerEvent`
- **fn** [[eos_ai-substrate-execution_events-py-build_execution_rejected_event]]`(result, request_event_id, session_name, rejection_reason, run_id) → SchedulerEvent`
- **fn** [[eos_ai-substrate-execution_events-py-build_execution_retried_event]]`(request, original_execution_id, session_name, run_id) → SchedulerEvent`

## Import Statements

```python
from __future__ import annotations
from eos_ai.substrate.execution_contract import ExecutionRequest
from eos_ai.substrate.execution_contract import ExecutionResult
from eos_ai.substrate.event_scheduler import SchedulerEvent
```
