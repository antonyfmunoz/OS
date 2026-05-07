---
type: codebase-class
file: eos_ai/substrate/execution_authority.py
line: 340
generated: 2026-05-07
---

# ExecutionAuthority

**File:** [[eos_ai-substrate-execution_authority-py]] | **Line:** 340

Control-plane handler that dispatches execution requests.

Subscribes to lifecycle events that need physical execution (e.g. stability_reached).
Builds ExecutionRequest, routes via ExecutionRouter, records in-flight state,
emits EXECUTION_REQUESTED event.
...

## Methods

- [[eos_ai-substrate-execution_authority-py-ExecutionAuthority-__init__]]`(router) → None` — 
- [[eos_ai-substrate-execution_authority-py-ExecutionAuthority-make_handler]]`(primitive_name, execution_class, requires, constraints, required_capabilities) → Callable[[RuntimeStateStore, SchedulerEvent], SchedulerExecutionResult]` — Factory: produce a scheduler handler for a specific primitive.
