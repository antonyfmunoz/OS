---
type: codebase-function
file: eos_ai/skill_registry.py
line: 76
generated: 2026-05-07
---

# SkillRegistry.load_from_db

**File:** [[eos_ai-skill_registry-py]] | **Line:** 76
**Signature:** `load_from_db(org_id) → None`

**Class:** [[eos_ai-skill_registry-py-SkillRegistry]]

Query the skills table in Neon for the given org_id and merge with
file-based skills already loaded. DB skills override file skills on
name collision. Called automatically on init when org_id is provided.

## Calls

- [[eos_ai-skill_registry-py-SkillRegistry-_parse_name]]

## Called By

- [[eos_ai-skill_registry-py-SkillRegistry-__init__]]
