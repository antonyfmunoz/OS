---
type: codebase-class
file: eos_ai/substrate/execution_result_handler.py
line: 52
generated: 2026-05-07
---

# ExecutionResultHandler

**File:** [[eos_ai-substrate-execution_result_handler-py]] | **Line:** 52

Control-plane handler that processes execution results.

Subscribes to execution result events. Validates, deduplicates,
writes outputs to state, emits lifecycle follow-up events.

...

## Methods

- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-__init__]]`(primitive_emission_map, primitive_conditional_map) → None` — 
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-handle_result]]`(store, event) → SchedulerExecutionResult` — Unified handler for all execution result event types.
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_handle_succeeded]]`(store, event, result, in_flight) → SchedulerExecutionResult` — Write outputs to state, mark complete, emit lifecycle events.
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_handle_failed]]`(store, event, result, in_flight) → SchedulerExecutionResult` — Retry if class allows and retries remain, else permanent failure.
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_handle_timed_out]]`(store, event, result, in_flight) → SchedulerExecutionResult` — Treat timeout as failure — same retry logic.
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_handle_rejected]]`(store, event, result, in_flight) → SchedulerExecutionResult` — Route to fallback if available, else permanent failure.
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_permanent_failure]]`(result, in_flight) → SchedulerExecutionResult` — Mark execution as permanently failed.
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_build_retry]]`(event, result, in_flight, retry_count) → SchedulerExecutionResult` — Build a retry request from the original in-flight record.
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_build_fallback_retry]]`(event, result, in_flight, fallback_node_id, fallback_transport) → SchedulerExecutionResult` — Build a retry targeting the fallback node.
- [[eos_ai-substrate-execution_result_handler-py-ExecutionResultHandler-_evaluate_condition]]`(condition, outputs, store) → bool` — Evaluate a simple string condition against outputs and store.
