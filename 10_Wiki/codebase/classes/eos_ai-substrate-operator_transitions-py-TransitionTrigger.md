---
type: codebase-class
file: eos_ai/substrate/operator_transitions.py
line: 64
generated: 2026-05-07
---

# TransitionTrigger

**File:** [[eos_ai-substrate-operator_transitions-py]] | **Line:** 64

Bounded trigger record passed to decide_transition.

`kind` is a short closed-set tag. `payload` carries the small set of
fields the decision function needs (action_taken, ritual_state, etc.).

## Decorators

- `@dataclass`
