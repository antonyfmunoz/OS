---
type: codebase-class
file: eos_ai/agent_runtime.py
line: 146
generated: 2026-04-12
---

# AgentRuntime

**File:** [[eos_ai-agent_runtime-py]] | **Line:** 146

*No docstring.*

## Methods

- [[eos_ai-agent_runtime-py-AgentRuntime-__init__]]`(ctx) → None` — 
- [[eos_ai-agent_runtime-py-AgentRuntime-client]]`()` — Legacy: exposes an Anthropic client for services that manage their
- [[eos_ai-agent_runtime-py-AgentRuntime-run]]`(task_type, prompt, venture_id, skill_name, max_tokens, agent, system_extra, ctx, modality, data_tier, require_realtime, forced_model, task_criticality) → AgentResult` — Execute a task with the appropriate model.
- [[eos_ai-agent_runtime-py-AgentRuntime-run_team_task]]`(team, sub_agent, prompt, venture_id, username) → AgentResult` — Route a task to the correct sub-agent within a domain team.
- [[eos_ai-agent_runtime-py-AgentRuntime-run_with_auto_skill]]`(task_type, prompt, venture_id, max_tokens, agent, username, ctx) → AgentResult` — Same as run() but auto-selects the top matching skill from the registry
