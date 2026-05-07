---
type: codebase-function
file: eos_ai/substrate/operator_transitions.py
line: 316
generated: 2026-05-07
---

# apply_wake_event

**File:** [[eos_ai-substrate-operator_transitions-py]] | **Line:** 316
**Signature:** `apply_wake_event(event) → None`

Push a WakeProducerEvent into the operator state. Best-effort.

## Calls

- [[eos_ai-substrate-operator_state-py-OperatorStateStore-get_or_create]]
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-put]]
- [[eos_ai-substrate-operator_state-py-_log]]
- [[eos_ai-substrate-operator_state-py-get_operator_state_store]]
- [[eos_ai-substrate-operator_transitions-py-_log]]
- [[eos_ai-substrate-operator_transitions-py-_record_transition]]
- [[eos_ai-substrate-operator_transitions-py-decide_transition]]
