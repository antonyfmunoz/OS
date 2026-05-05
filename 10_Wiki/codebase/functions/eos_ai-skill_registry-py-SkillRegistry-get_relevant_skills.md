---
type: codebase-function
file: eos_ai/skill_registry.py
line: 184
generated: 2026-04-12
---

# SkillRegistry.get_relevant_skills

**File:** [[eos_ai-skill_registry-py]] | **Line:** 184
**Signature:** `get_relevant_skills(task_description, top_n) → list[Skill]`

**Class:** [[eos_ai-skill_registry-py-SkillRegistry]]

Returns the top_n skills most relevant to task_description.

Uses semantic cosine similarity when embeddings are cached (primary path).
Falls back to keyword overlap when embeddings are unavailable.

## Called By

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-agent_runtime-py-AgentRuntime-run_with_auto_skill]]
