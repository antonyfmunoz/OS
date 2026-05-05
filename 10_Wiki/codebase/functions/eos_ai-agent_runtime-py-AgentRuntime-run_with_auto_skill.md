---
type: codebase-function
file: eos_ai/agent_runtime.py
line: 465
generated: 2026-04-12
---

# AgentRuntime.run_with_auto_skill

**File:** [[eos_ai-agent_runtime-py]] | **Line:** 465
**Signature:** `run_with_auto_skill(task_type, prompt, venture_id, max_tokens, agent, username, ctx) → AgentResult`

**Class:** [[eos_ai-agent_runtime-py-AgentRuntime]]

Same as run() but auto-selects the top matching skill from the registry
based on keyword overlap with the prompt.

If username is provided and the task is outreach-oriented (GENERATE),
the human profile for that lead is loaded and injected into the system
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-context-py-load_context_from_env]]
- [[eos_ai-skill_registry-py-SkillRegistry-get_relevant_skills]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
