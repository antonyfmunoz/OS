---
type: codebase-function
file: eos_ai/substrate/execution_events.py
line: 45
generated: 2026-05-07
---

# build_execution_completed_event

**File:** [[eos_ai-substrate-execution_events-py]] | **Line:** 45
**Signature:** `build_execution_completed_event(result, request_event_id, session_name, run_id) → SchedulerEvent`

Build EXECUTION_COMPLETED event from an ExecutionResult.

## Calls

- [[eos_ai-substrate-execution_contract-py-ExecutionRequest-to_dict]]
- [[eos_ai-substrate-execution_contract-py-ExecutionResult-to_dict]]

## Called By

- [[eos_ai-substrate-execution_worker-py-ExecutionWorker-handle_execution_requested]]
