---
type: codebase-function
file: eos_ai/skill_registry_v2.py
line: 87
generated: 2026-04-12
---

# SkillRegistryV2.register

**File:** [[eos_ai-skill_registry_v2-py]] | **Line:** 87
**Signature:** `register(skill) → bool`

**Class:** [[eos_ai-skill_registry_v2-py-SkillRegistryV2]]

Upsert a SkillV2 into the Neon skills table.
Uses the existing skills schema: (id, org_id, name, content, version).

## Calls

- [[eos_ai-skill_registry_v2-py-SkillV2-to_markdown]]

## Called By

- [[eos_ai-skill_registry_v2-py-SkillRegistryV2-seed_core_skills]]
