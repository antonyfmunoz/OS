---
type: codebase-function
file: eos_ai/substrate/execution_worker.py
line: 96
generated: 2026-05-07
---

# ExecutionWorker.handle_execution_requested

**File:** [[eos_ai-substrate-execution_worker-py]] | **Line:** 96
**Signature:** `handle_execution_requested(store, event) → SchedulerExecutionResult`

**Class:** [[eos_ai-substrate-execution_worker-py-ExecutionWorker]]

Main scheduler handler. Signature matches HandlerFn type.

Steps:
1. Deserialize request from event payload
2. Find adapter for target node
...

## Calls

- [[eos_ai-substrate-event_scheduler-py-_log]]
- [[eos_ai-substrate-execution_adapter-py-ExecutionAdapter-execute]]
- [[eos_ai-substrate-execution_adapter-py-LocalRuntimeAdapter-execute]]
- [[eos_ai-substrate-execution_adapter-py-WorkstationAdapter-execute]]
- [[eos_ai-substrate-execution_adapter-py-_iso_now]]
- [[eos_ai-substrate-execution_adapter-py-_log]]
- [[eos_ai-substrate-execution_contract-py-ExecutionRequest-from_dict]]
- [[eos_ai-substrate-execution_contract-py-ExecutionResult-from_dict]]
- [[eos_ai-substrate-execution_events-py-build_execution_completed_event]]
- [[eos_ai-substrate-execution_events-py-build_execution_failed_event]]
- [[eos_ai-substrate-execution_events-py-build_execution_rejected_event]]
- [[eos_ai-substrate-execution_events-py-build_execution_timed_out_event]]
- [[eos_ai-substrate-execution_worker-py-_iso_now]]
- [[eos_ai-substrate-execution_worker-py-_log]]
