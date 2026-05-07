---
type: codebase-class
file: eos_ai/substrate/execution_worker.py
line: 71
generated: 2026-05-07
---

# ExecutionWorker

**File:** [[eos_ai-substrate-execution_worker-py]] | **Line:** 71

Scheduler handler that bridges execution requests to adapters.

INVARIANTS:
- NEVER returns mutations (mutations list is always empty)
- NEVER evaluates lifecycle guards
...

## Methods

- [[eos_ai-substrate-execution_worker-py-ExecutionWorker-__init__]]`(store) → None` — 
- [[eos_ai-substrate-execution_worker-py-ExecutionWorker-register_adapter]]`(adapter) → None` — Register an adapter for a node.
- [[eos_ai-substrate-execution_worker-py-ExecutionWorker-get_adapter]]`(node_id) → Optional[ExecutionAdapter]` — Get adapter for a node, or None.
- [[eos_ai-substrate-execution_worker-py-ExecutionWorker-handle_execution_requested]]`(store, event) → SchedulerExecutionResult` — Main scheduler handler. Signature matches HandlerFn type.
