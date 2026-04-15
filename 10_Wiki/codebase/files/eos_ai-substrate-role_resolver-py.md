---
type: codebase-file
path: eos_ai/substrate/role_resolver.py
module: eos_ai.substrate.role_resolver
lines: 75
size: 2605
generated: 2026-04-12
---

# eos_ai/substrate/role_resolver.py

Role resolver — bridges existing agent_hierarchy ids to substrate AgentRoles.

The current codebase routes through agent_hierarchy.AgentHierarchy, which
uses long-form agent ids like `executive_assistant`, `lyfe_institute_ceo`,
`empyrean_ceo`, `portfolio_advisor`. The substrate uses three abstract role
...

**Lines:** 75 | **Size:** 2,605 bytes

## Depends On

- [[eos_ai-substrate-roles-py]]

## Contains

- **fn** [[eos_ai-substrate-role_resolver-py-resolve_role]]`(hierarchy_id) → Optional[AgentRole]`
- **fn** [[eos_ai-substrate-role_resolver-py-substrate_slug_for]]`(hierarchy_id) → Optional[str]`
- **fn** [[eos_ai-substrate-role_resolver-py-all_mappings]]`() → dict[str, str]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import replace
from typing import Optional
from eos_ai.substrate.roles import AgentRole
from eos_ai.substrate.roles import RoleRegistry
```
