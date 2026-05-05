---
type: codebase-function
file: eos_ai/skill_registry.py
line: 237
generated: 2026-04-12
---

# get_skill_registry

**File:** [[eos_ai-skill_registry-py]] | **Line:** 237
**Signature:** `get_skill_registry(org_id) → SkillRegistry`

Return the module-level singleton SkillRegistry.

Instantiated once; reused on every subsequent call.
To force a reload after /sync or skill rewrites, call
reset_skill_registry() then get_skill_registry() again.

## Called By

- [[eos_ai-agent_runtime-py-AgentRuntime-__init__]]
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-__init__]]
