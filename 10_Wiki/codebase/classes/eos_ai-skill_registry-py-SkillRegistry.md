---
type: codebase-class
file: eos_ai/skill_registry.py
line: 22
generated: 2026-05-07
---

# SkillRegistry

**File:** [[eos_ai-skill_registry-py]] | **Line:** 22

*No docstring.*

## Methods

- [[eos_ai-skill_registry-py-SkillRegistry-__init__]]`(org_id) → None` — 
- [[eos_ai-skill_registry-py-SkillRegistry-_load]]`() → None` — 
- [[eos_ai-skill_registry-py-SkillRegistry-_to_skill_id]]`(path) → str` — 
- [[eos_ai-skill_registry-py-SkillRegistry-load_from_db]]`(org_id) → None` — Query the skills table in Neon for the given org_id and merge with
- [[eos_ai-skill_registry-py-SkillRegistry-_cache_embeddings]]`() → None` — Embed each skill's name + first 800 chars of content on registry load.
- [[eos_ai-skill_registry-py-SkillRegistry-_parse_name]]`(content, path) → str` — 
- [[eos_ai-skill_registry-py-SkillRegistry-get_skill]]`(name) → Skill | None` — Fuzzy name matching: tries exact skill_id, then normalized
- [[eos_ai-skill_registry-py-SkillRegistry-get_relevant_skills]]`(task_description, top_n) → list[Skill]` — Returns the top_n skills most relevant to task_description.
- [[eos_ai-skill_registry-py-SkillRegistry-list_skills]]`() → list[str]` — 
- [[eos_ai-skill_registry-py-SkillRegistry-all_skills]]`() → list[Skill]` — 
