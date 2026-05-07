---
type: codebase-function
file: eos_ai/substrate/approved_action_executor.py
line: 135
generated: 2026-05-07
---

# build_action_executed_result

**File:** [[eos_ai-substrate-approved_action_executor-py]] | **Line:** 135
**Signature:** `build_action_executed_result(work_order_id, action, backend, success, detail, target_account, chrome_path) → dict[str, Any]`

Build an ACTION_EXECUTED result message for the outbox.

## Calls

- [[eos_ai-substrate-approved_action_executor-py-_now_iso]]

## Called By

- [[eos_ai-substrate-approved_action_executor-py-execute_approved_action]]
