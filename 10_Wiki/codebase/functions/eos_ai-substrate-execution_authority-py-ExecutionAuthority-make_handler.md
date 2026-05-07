---
type: codebase-function
file: eos_ai/substrate/execution_authority.py
line: 355
generated: 2026-05-07
---

# ExecutionAuthority.make_handler

**File:** [[eos_ai-substrate-execution_authority-py]] | **Line:** 355
**Signature:** `make_handler(primitive_name, execution_class, requires, constraints, required_capabilities) → Callable[[RuntimeStateStore, SchedulerEvent], SchedulerExecutionResult]`

**Class:** [[eos_ai-substrate-execution_authority-py-ExecutionAuthority]]

Factory: produce a scheduler handler for a specific primitive.

Returns a callable matching HandlerFn signature:
    (store: RuntimeStateStore, event: SchedulerEvent) -> SchedulerExecutionResult

...

## Calls

- [[eos_ai-substrate-event_scheduler-py-_log]]
- [[eos_ai-substrate-execution_authority-py-_log]]
- [[eos_ai-substrate-execution_contract-py-ExecutionRequest-to_dict]]
- [[eos_ai-substrate-execution_contract-py-ExecutionResult-to_dict]]
- [[eos_ai-substrate-execution_contract-py-_compute_idempotency_key]]
- [[eos_ai-substrate-execution_contract-py-_new_execution_id]]
- [[eos_ai-substrate-execution_events-py-build_execution_requested_event]]
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-route]]
