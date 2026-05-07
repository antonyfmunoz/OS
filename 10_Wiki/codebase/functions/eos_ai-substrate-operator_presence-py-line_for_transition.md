---
type: codebase-function
file: eos_ai/substrate/operator_presence.py
line: 90
generated: 2026-05-07
---

# line_for_transition

**File:** [[eos_ai-substrate-operator_presence-py]] | **Line:** 90
**Signature:** `line_for_transition(from_mode, to_mode) → Optional[str]`

Return a deterministic hybrid line for a (from_mode, to_mode) pair.

Returns None if no template is registered. Callers must treat None as
"stay silent" — that is the correct premium default.

## Calls

- [[eos_ai-substrate-operator_state-py-OperatorStateStore-get]]

## Called By

- [[eos_ai-substrate-operator_presence-py-intro_for_transition]]
- [[scripts-substrate_operator_state_smoke_test-py-main]]
