---
type: codebase-function
file: eos_ai/skill_improvement.py
line: 356
generated: 2026-04-12
---

# SkillImprovementEngine.propose_new_skill

**File:** [[eos_ai-skill_improvement-py]] | **Line:** 356
**Signature:** `propose_new_skill(pattern) → dict`

**Class:** [[eos_ai-skill_improvement-py-SkillImprovementEngine]]

Use AgentRuntime to write a new skill file from a detected pattern.
Writes to skills/Generated/<skill_id>.md.
Logs a skill_created event to memory.db.

Returns {action, skill_id, file_path, pattern}.

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-_log_skill_created]]

## Called By

- [[eos_ai-skill_improvement-py-SkillImprovementEngine-run_self_organization_cycle]]
