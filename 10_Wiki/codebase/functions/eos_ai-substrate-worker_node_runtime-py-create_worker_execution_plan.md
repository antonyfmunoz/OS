---
type: codebase-function
file: eos_ai/substrate/worker_node_runtime.py
line: 69
generated: 2026-05-07
---

# create_worker_execution_plan

**File:** [[eos_ai-substrate-worker_node_runtime-py]] | **Line:** 69
**Signature:** `create_worker_execution_plan(work_order, worker_profile) → list[WorkerAction]`

Create a sequence of actions from a work order.

Returns actions in execution order. Actions that require approval
are marked with requires_approval=True.
