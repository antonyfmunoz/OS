---
type: codebase-class
file: eos_ai/skill_registry_v2.py
line: 80
generated: 2026-04-11
---

# SkillRegistryV2

**File:** [[eos_ai-skill_registry_v2-py]] | **Line:** 80

*No docstring.*

## Methods

- [[eos_ai-skill_registry_v2-py-SkillRegistryV2-__init__]]`(ctx) → None` — 
- [[eos_ai-skill_registry_v2-py-SkillRegistryV2-register]]`(skill) → bool` — Upsert a SkillV2 into the Neon skills table.
- [[eos_ai-skill_registry_v2-py-SkillRegistryV2-get_skill_stats]]`(skill_id) → dict` — Derive performance stats from the interactions table.
- [[eos_ai-skill_registry_v2-py-SkillRegistryV2-get_all_stats]]`() → list[dict]` — Return performance stats for every registered V2 skill.
- [[eos_ai-skill_registry_v2-py-SkillRegistryV2-seed_core_skills]]`() → int` — Register Stage 1 core skills as first-class Neon objects.
