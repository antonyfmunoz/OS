---
type: codebase-function
file: eos_ai/substrate/role_resolver.py
line: 43
generated: 2026-05-07
---

# resolve_role

**File:** [[eos_ai-substrate-role_resolver-py]] | **Line:** 43
**Signature:** `resolve_role(hierarchy_id) → Optional[AgentRole]`

Return the substrate AgentRole for a given agent_hierarchy id.

For CEO slots, the resolved role is cloned with `metadata["concrete_id"]`
set to the original hierarchy id, so callers can still distinguish
lyfe_institute_ceo from empyrean_ceo at the substrate layer without
...

## Calls

- [[eos_ai-substrate-roles-py-RoleRegistry-default]]
- [[eos_ai-substrate-roles-py-RoleRegistry-get]]
