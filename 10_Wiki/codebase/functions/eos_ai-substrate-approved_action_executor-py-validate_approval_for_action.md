---
type: codebase-function
file: eos_ai/substrate/approved_action_executor.py
line: 91
generated: 2026-05-07
---

# validate_approval_for_action

**File:** [[eos_ai-substrate-approved_action_executor-py]] | **Line:** 91
**Signature:** `validate_approval_for_action(response, expected_action, expected_work_order_id) → list[str]`

Validate that the approval response authorizes the expected action.

Returns list of errors. Empty list = valid.

## Calls

- [[eos_ai-substrate-approved_action_executor-py-extract_approved_action]]
- [[eos_ai-substrate-approved_action_executor-py-extract_decision]]
- [[eos_ai-substrate-approved_action_executor-py-extract_work_order_id]]

## Called By

- [[eos_ai-substrate-approved_action_executor-py-execute_approved_action]]
