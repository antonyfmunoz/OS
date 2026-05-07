---
type: codebase-function
file: eos_ai/substrate/execution_events.py
line: 120
generated: 2026-05-07
---

# build_execution_rejected_event

**File:** [[eos_ai-substrate-execution_events-py]] | **Line:** 120
**Signature:** `build_execution_rejected_event(result, request_event_id, session_name, rejection_reason, run_id) → SchedulerEvent`

Build EXECUTION_REJECTED event.

## Calls

- [[eos_ai-substrate-execution_contract-py-ExecutionRequest-to_dict]]
- [[eos_ai-substrate-execution_contract-py-ExecutionResult-to_dict]]

## Called By

- [[eos_ai-substrate-execution_worker-py-ExecutionWorker-handle_execution_requested]]
