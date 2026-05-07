---
type: codebase-function
file: eos_ai/substrate/execution_adapter.py
line: 294
generated: 2026-05-07
---

# WorkstationAdapter.execute

**File:** [[eos_ai-substrate-execution_adapter-py]] | **Line:** 294
**Signature:** `execute(request) → ExecutionResult`

**Class:** [[eos_ai-substrate-execution_adapter-py-WorkstationAdapter]]

Execute a request via HTTP to the workstation daemon. Never raises.

## Calls

- [[eos_ai-substrate-execution_adapter-py-_iso_now]]
- [[eos_ai-substrate-execution_adapter-py-_log]]
- [[eos_ai-substrate-execution_adapter-py-_make_result]]

## Called By

- [[eos_ai-substrate-execution_worker-py-ExecutionWorker-handle_execution_requested]]
