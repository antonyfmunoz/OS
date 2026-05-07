---
type: codebase-function
file: eos_ai/skill_improvement.py
line: 234
generated: 2026-05-07
---

# SkillImprovementEngine.run_improvement_cycle

**File:** [[eos_ai-skill_improvement-py]] | **Line:** 234
**Signature:** `run_improvement_cycle() → list[dict]`

**Class:** [[eos_ai-skill_improvement-py-SkillImprovementEngine]]

Run check_and_improve() on every loaded skill.
Returns list of result dicts — one per skill.

## Calls

- [[eos_ai-skill_improvement-py-SkillImprovementEngine-check_and_improve]]
- [[eos_ai-skill_registry-py-SkillRegistry-list_skills]]

## Called By

- [[eos_ai-evolution_engine-py-EvolutionEngine-run_weekly_evolution_cycle]]
