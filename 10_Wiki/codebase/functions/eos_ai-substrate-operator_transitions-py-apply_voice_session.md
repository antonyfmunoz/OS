---
type: codebase-function
file: eos_ai/substrate/operator_transitions.py
line: 356
generated: 2026-04-12
---

# apply_voice_session

**File:** [[eos_ai-substrate-operator_transitions-py]] | **Line:** 356
**Signature:** `apply_voice_session(session) → None`

Push a VoiceSession update into operator state.

`lifecycle` is one of: "started", "turn", "ended".

## Calls

- [[eos_ai-substrate-operator_state-py-OperatorStateStore-get]]
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-get_or_create]]
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-put]]
- [[eos_ai-substrate-operator_state-py-_log]]
- [[eos_ai-substrate-operator_state-py-get_operator_state_store]]
- [[eos_ai-substrate-operator_transitions-py-_log]]
- [[eos_ai-substrate-operator_transitions-py-_record_transition]]
- [[eos_ai-substrate-operator_transitions-py-decide_transition]]
