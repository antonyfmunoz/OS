---
type: codebase-function
file: eos_ai/substrate/capability_routing.py
line: 171
generated: 2026-05-07
---

# route_task

**File:** [[eos_ai-substrate-capability_routing-py]] | **Line:** 171
**Signature:** `route_task(task, session, local_available) → 'Task'`

Attach routing metadata to a task. Mutates and returns the task.

Sets:
- task.required_capabilities
- task.chosen_target
...

## Calls

- [[eos_ai-substrate-capability_routing-py-_build_reason]]
- [[eos_ai-substrate-capability_routing-py-_log]]
- [[eos_ai-substrate-capability_routing-py-choose_execution_target]]
- [[eos_ai-substrate-capability_routing-py-infer_task_capabilities]]
