---
type: codebase-function
file: eos_ai/platforms/eos/execution_bridge.py
line: 229
generated: 2026-05-07
---

# execute_created_work_immediately

**File:** [[eos_ai-platforms-eos-execution_bridge-py]] | **Line:** 229
**Signature:** `execute_created_work_immediately(task_ids, pipeline_ids) → ExecutionBridgeResult`

Execute newly-created tasks and pipelines without waiting for the scheduler.

Best-effort — individual failures are captured in the result, never raised.

Args:
...

## Calls

- [[eos_ai-platforms-eos-execution_bridge-py-_execute_single_pipeline]]
- [[eos_ai-platforms-eos-execution_bridge-py-_execute_single_task]]
- [[eos_ai-platforms-eos-execution_bridge-py-_get_operator_session]]
- [[eos_ai-platforms-eos-execution_bridge-py-_get_routing_decision]]
- [[eos_ai-platforms-eos-execution_bridge-py-_log]]
- [[eos_ai-platforms-eos-execution_bridge-py-_stream]]
