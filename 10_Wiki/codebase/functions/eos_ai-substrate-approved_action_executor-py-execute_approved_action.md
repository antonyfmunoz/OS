---
type: codebase-function
file: eos_ai/substrate/approved_action_executor.py
line: 249
generated: 2026-05-07
---

# execute_approved_action

**File:** [[eos_ai-substrate-approved_action_executor-py]] | **Line:** 249
**Signature:** `execute_approved_action(response, action, executor_fn, work_order_id) → dict[str, Any]`

Execute a single approved action after full validation.

Returns a result dict with success/failure and messages to write.

## Calls

- [[eos_ai-substrate-approved_action_executor-py-build_action_executed_result]]
- [[eos_ai-substrate-approved_action_executor-py-build_backend_missing_result]]
- [[eos_ai-substrate-approved_action_executor-py-build_next_gate_request]]
- [[eos_ai-substrate-approved_action_executor-py-validate_approval_for_action]]
