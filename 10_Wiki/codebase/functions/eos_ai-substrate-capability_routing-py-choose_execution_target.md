---
type: codebase-function
file: eos_ai/substrate/capability_routing.py
line: 115
generated: 2026-05-07
---

# choose_execution_target

**File:** [[eos_ai-substrate-capability_routing-py]] | **Line:** 115
**Signature:** `choose_execution_target(task, session, local_available) → ExecutionTarget`

Choose the best execution target for a task.

Resolution order:
1. Infer capabilities from task text.
2. Determine context lane (builder vs product).
...

## Calls

- [[eos_ai-substrate-capability_routing-py-infer_task_capabilities]]

## Called By

- [[eos_ai-substrate-capability_routing-py-route_task]]
