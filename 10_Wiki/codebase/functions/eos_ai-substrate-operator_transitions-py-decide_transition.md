---
type: codebase-function
file: eos_ai/substrate/operator_transitions.py
line: 90
generated: 2026-05-07
---

# decide_transition

**File:** [[eos_ai-substrate-operator_transitions-py]] | **Line:** 90
**Signature:** `decide_transition(state, trigger) → TransitionDecision`

Pure decision: given current state + trigger, what mode comes next?

This is intentionally a small `if` ladder, NOT a rules engine. Each
branch is one explicit, explainable transition. Adding behavior means
adding a branch here, not registering a callback anywhere.

## Calls

- [[eos_ai-substrate-operator_state-py-OperatorStateStore-get]]

## Called By

- [[eos_ai-substrate-operator_transitions-py-apply_ritual]]
- [[eos_ai-substrate-operator_transitions-py-apply_voice_session]]
- [[eos_ai-substrate-operator_transitions-py-apply_wake_event]]
- [[scripts-substrate_audio_loop_smoke_test-py-main]]
