---
type: codebase-class
file: eos_ai/substrate/operator_state.py
line: 121
generated: 2026-04-12
---

# OperatorState

**File:** [[eos_ai-substrate-operator_state-py]] | **Line:** 121

Unified bounded operator state for a single node.

All fields except `node_id` are optional: the state is monotonically
enriched as wake/voice/ritual/readiness signals flow in.

## Methods

- [[eos_ai-substrate-operator_state-py-OperatorState-is_active]]`() → bool` — 
- [[eos_ai-substrate-operator_state-py-OperatorState-last_transition]]`() → Optional[OperatorTransition]` — 
- [[eos_ai-substrate-operator_state-py-OperatorState-append_transition]]`(transition) → None` — 
- [[eos_ai-substrate-operator_state-py-OperatorState-as_dict]]`() → dict` — 
- [[eos_ai-substrate-operator_state-py-OperatorState-from_dict]]`(d) → 'OperatorState'` — 

## Decorators

- `@dataclass`
