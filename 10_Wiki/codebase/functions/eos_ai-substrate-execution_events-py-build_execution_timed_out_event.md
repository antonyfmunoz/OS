---
type: codebase-function
file: eos_ai/substrate/execution_events.py
line: 95
generated: 2026-05-07
---

# build_execution_timed_out_event

**File:** [[eos_ai-substrate-execution_events-py]] | **Line:** 95
**Signature:** `build_execution_timed_out_event(result, request_event_id, session_name, run_id) → SchedulerEvent`

Build EXECUTION_TIMED_OUT event.

## Calls

- [[eos_ai-substrate-execution_contract-py-ExecutionRequest-to_dict]]
- [[eos_ai-substrate-execution_contract-py-ExecutionResult-to_dict]]

## Called By

- [[eos_ai-substrate-execution_worker-py-ExecutionWorker-handle_execution_requested]]
