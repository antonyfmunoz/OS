---
type: codebase-function
file: eos_ai/substrate/execution_events.py
line: 146
generated: 2026-05-07
---

# build_execution_retried_event

**File:** [[eos_ai-substrate-execution_events-py]] | **Line:** 146
**Signature:** `build_execution_retried_event(request, original_execution_id, session_name, run_id) → SchedulerEvent`

Build EXECUTION_RETRIED event (a new request with incremented retry_count).

## Calls

- [[eos_ai-substrate-execution_contract-py-ExecutionRequest-to_dict]]
- [[eos_ai-substrate-execution_contract-py-ExecutionResult-to_dict]]

## Called By

- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_build_fallback_retry]]
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_build_retry]]
