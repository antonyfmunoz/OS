---
type: codebase-function
file: eos_ai/skill_improvement.py
line: 121
generated: 2026-04-12
---

# SkillImprovementEngine.check_and_improve

**File:** [[eos_ai-skill_improvement-py]] | **Line:** 121
**Signature:** `check_and_improve(skill_id) → dict`

**Class:** [[eos_ai-skill_improvement-py-SkillImprovementEngine]]

Evaluate a skill's outcome data and rewrite it if underperforming.

Returns a result dict:
  action:     "improved" | "skipped_insufficient_data" | "skipped_above_threshold" | "error"
  skill_id:   the skill_id checked
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-_build_prompt]]
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-_fetch_skill_outcomes]]
- [[eos_ai-skill_registry-py-SkillRegistry-get_skill]]
- [[eos_ai-skill_registry-py-reset_skill_registry]]

## Called By

- [[eos_ai-skill_improvement-py-SkillImprovementEngine-run_improvement_cycle]]
