---
type: codebase-function
file: eos_ai/skill_improvement.py
line: 260
generated: 2026-04-12
---

# SkillImprovementEngine.detect_patterns

**File:** [[eos_ai-skill_improvement-py]] | **Line:** 260
**Signature:** `detect_patterns() → list[dict]`

**Class:** [[eos_ai-skill_improvement-py-SkillImprovementEngine]]

Query Neon interactions from the last 30 days.
Find recurring task types with no skill_id — these are candidates
for a new auto-generated skill.

Returns list of dicts:
...

## Called By

- [[eos_ai-skill_improvement-py-SkillImprovementEngine-run_self_organization_cycle]]
