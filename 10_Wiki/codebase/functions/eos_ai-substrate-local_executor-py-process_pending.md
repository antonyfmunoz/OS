---
type: codebase-function
file: eos_ai/substrate/local_executor.py
line: 195
generated: 2026-04-11
---

# process_pending

**File:** [[eos_ai-substrate-local_executor-py]] | **Line:** 195
**Signature:** `process_pending(node_id) → dict[str, Any]`

Drain up to MAX_BATCH pending commands for `node_id`. Operator-triggered.
Returns {"node_id", "processed", "results": [...]}.

## Calls

- [[eos_ai-substrate-local_executor-py-execute_command]]
