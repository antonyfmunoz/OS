---
type: codebase-class
file: eos_ai/substrate/roles.py
line: 71
generated: 2026-04-12
---

# RoleRegistry

**File:** [[eos_ai-substrate-roles-py]] | **Line:** 71

Minimal in-memory role registry, seeded with the three initial roles.

These mirror agent_hierarchy.py at a higher level of abstraction:
  - ea_orchestrator  ≈ executive_assistant (DEX), the primary interface
  - ceo              ≈ a generic CEO slot; per-company CEOs are instances
...

## Methods

- [[eos_ai-substrate-roles-py-RoleRegistry-__init__]]`() → None` — 
- [[eos_ai-substrate-roles-py-RoleRegistry-register]]`(role) → AgentRole` — 
- [[eos_ai-substrate-roles-py-RoleRegistry-get]]`(slug) → Optional[AgentRole]` — 
- [[eos_ai-substrate-roles-py-RoleRegistry-all]]`() → list[AgentRole]` — 
- [[eos_ai-substrate-roles-py-RoleRegistry-default]]`() → 'RoleRegistry'` — 
