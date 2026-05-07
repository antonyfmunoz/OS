---
type: codebase-function
file: eos_ai/substrate/execution_adapter.py
line: 156
generated: 2026-05-07
---

# LocalRuntimeAdapter.execute

**File:** [[eos_ai-substrate-execution_adapter-py]] | **Line:** 156
**Signature:** `execute(request) → ExecutionResult`

**Class:** [[eos_ai-substrate-execution_adapter-py-LocalRuntimeAdapter]]

Execute a request via local_executor. Never raises.

## Calls

- [[eos_ai-substrate-execution_adapter-py-_iso_now]]
- [[eos_ai-substrate-execution_adapter-py-_log]]
- [[eos_ai-substrate-execution_adapter-py-_make_result]]

## Called By

- [[eos_ai-substrate-execution_worker-py-ExecutionWorker-handle_execution_requested]]
