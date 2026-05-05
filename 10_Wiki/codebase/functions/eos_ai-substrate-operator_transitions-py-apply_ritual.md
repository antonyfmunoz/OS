---
type: codebase-function
file: eos_ai/substrate/operator_transitions.py
line: 402
generated: 2026-04-12
---

# apply_ritual

**File:** [[eos_ai-substrate-operator_transitions-py]] | **Line:** 402
**Signature:** `apply_ritual(node_id) → None`

Push a ritual lifecycle update into operator state. Best-effort.

`node_id` may be None if the ritual is not bound to a station; in that
case we no-op (operator state is per-node).

## Calls

- [[eos_ai-substrate-operator_state-py-OperatorStateStore-get_or_create]]
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-put]]
- [[eos_ai-substrate-operator_state-py-_log]]
- [[eos_ai-substrate-operator_state-py-get_operator_state_store]]
- [[eos_ai-substrate-operator_transitions-py-_log]]
- [[eos_ai-substrate-operator_transitions-py-_record_transition]]
- [[eos_ai-substrate-operator_transitions-py-decide_transition]]
