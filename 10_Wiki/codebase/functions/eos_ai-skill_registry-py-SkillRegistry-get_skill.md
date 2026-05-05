---
type: codebase-function
file: eos_ai/skill_registry.py
line: 133
generated: 2026-04-12
---

# SkillRegistry.get_skill

**File:** [[eos_ai-skill_registry-py]] | **Line:** 133
**Signature:** `get_skill(name) → Skill | None`

**Class:** [[eos_ai-skill_registry-py-SkillRegistry]]

Fuzzy name matching: tries exact skill_id, then normalized
(- and _ equivalent), then partial substring match on
skill_id and skill name, case-insensitive.
Returns the best single match or None.

## Called By

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-check_and_improve]]
