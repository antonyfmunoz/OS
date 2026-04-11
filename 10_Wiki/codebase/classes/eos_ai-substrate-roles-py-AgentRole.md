---
type: codebase-class
file: eos_ai/substrate/roles.py
line: 48
generated: 2026-04-11
---

# AgentRole

**File:** [[eos_ai-substrate-roles-py]] | **Line:** 48

A role a running agent instance can adopt.

`slug` is the stable identifier used across the substrate (appears in
SafeAction.issued_by, StationEvent.payload, ritual inputs, etc.).

## Methods

- [[eos_ai-substrate-roles-py-AgentRole-has_scope]]`(scope) → bool` — 
- [[eos_ai-substrate-roles-py-AgentRole-can_handoff_to]]`(other_slug) → bool` — 

## Decorators

- `@dataclass`
