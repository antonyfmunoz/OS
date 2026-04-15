---
type: codebase-class
file: eos_ai/skill_improvement.py
line: 34
generated: 2026-04-12
---

# SkillImprovementEngine

**File:** [[eos_ai-skill_improvement-py]] | **Line:** 34

*No docstring.*

## Methods

- [[eos_ai-skill_improvement-py-SkillImprovementEngine-__init__]]`() → None` — 
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-_fetch_skill_outcomes]]`(skill_id) → list[dict]` — Return all interactions + outcomes for skill_id from Neon.
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-_build_prompt]]`(skill, winners, losers, reply_rate) → str` — 
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-check_and_improve]]`(skill_id) → dict` — Evaluate a skill's outcome data and rewrite it if underperforming.
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-run_improvement_cycle]]`() → list[dict]` — Run check_and_improve() on every loaded skill.
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-detect_patterns]]`() → list[dict]` — Query Neon interactions from the last 30 days.
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-_log_skill_created]]`(skill_id, file_path, pattern) → None` — 
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-propose_new_skill]]`(pattern) → dict` — Use AgentRuntime to write a new skill file from a detected pattern.
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-run_self_organization_cycle]]`() → list[dict]` — Detect recurring unassigned patterns → propose a new skill for each.
