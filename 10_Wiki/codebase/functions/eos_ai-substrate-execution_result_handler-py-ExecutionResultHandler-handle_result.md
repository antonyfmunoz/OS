---
type: codebase-function
file: eos_ai/substrate/execution_result_handler.py
line: 79
generated: 2026-05-07
---

# ExecutionResultHandler.handle_result

**File:** [[eos_ai-substrate-execution_result_handler-py]] | **Line:** 79
**Signature:** `handle_result(store, event) → SchedulerExecutionResult`

**Class:** [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler]]

Unified handler for all execution result event types.

Signature matches HandlerFn: (store, event) -> SchedulerExecutionResult.
Routes by ExecutionStatus to the appropriate internal handler.

## Calls

- [[eos_ai-substrate-event_scheduler-py-_log]]
- [[eos_ai-substrate-execution_contract-py-ExecutionRequest-from_dict]]
- [[eos_ai-substrate-execution_contract-py-ExecutionResult-from_dict]]
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_handle_failed]]
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_handle_rejected]]
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_handle_succeeded]]
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_handle_timed_out]]
- [[eos_ai-substrate-execution_result_handler-py-_log]]
