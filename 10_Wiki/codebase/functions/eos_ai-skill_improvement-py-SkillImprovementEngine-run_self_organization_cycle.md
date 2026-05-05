---
type: codebase-function
file: eos_ai/skill_improvement.py
line: 423
generated: 2026-04-12
---

# SkillImprovementEngine.run_self_organization_cycle

**File:** [[eos_ai-skill_improvement-py]] | **Line:** 423
**Signature:** `run_self_organization_cycle() → list[dict]`

**Class:** [[eos_ai-skill_improvement-py-SkillImprovementEngine]]

Detect recurring unassigned patterns → propose a new skill for each.
Called weekly (Mondays) by the orchestrator morning cycle.
Returns list of created skill dicts.

## Calls

- [[eos_ai-skill_improvement-py-SkillImprovementEngine-detect_patterns]]
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-propose_new_skill]]
