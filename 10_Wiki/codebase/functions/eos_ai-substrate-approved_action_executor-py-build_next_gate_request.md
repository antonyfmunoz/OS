---
type: codebase-function
file: eos_ai/substrate/approved_action_executor.py
line: 192
generated: 2026-05-07
---

# build_next_gate_request

**File:** [[eos_ai-substrate-approved_action_executor-py]] | **Line:** 192
**Signature:** `build_next_gate_request(work_order_id, gate_action, description, target_account, possible_states) → dict[str, Any]`

Build a NEXT_GATE_REQUIRED approval request.

## Calls

- [[eos_ai-substrate-approved_action_executor-py-_now_iso]]

## Called By

- [[eos_ai-substrate-approved_action_executor-py-build_login_required_gate]]
- [[eos_ai-substrate-approved_action_executor-py-execute_approved_action]]
