---
type: codebase-class
file: eos_ai/agent_hierarchy.py
line: 273
generated: 2026-04-11
---

# AgentHierarchy

**File:** [[eos_ai-agent_hierarchy-py]] | **Line:** 273

Formal hierarchy of agents in the EntrepreneurOS system.

Responsibilities:
- Routing: which agent should handle a given request
- Context injection: format hierarchy context for an agent's system prompt
...

## Methods

- [[eos_ai-agent_hierarchy-py-AgentHierarchy-__init__]]`() → None` — 
- [[eos_ai-agent_hierarchy-py-AgentHierarchy-get_primary_interface]]`() → str` — Return the agent_id of the primary founder-facing interface (EA).
- [[eos_ai-agent_hierarchy-py-AgentHierarchy-should_handle_directly]]`(agent_id, task) → bool` — Return True if agent_id should handle this task without escalation.
- [[eos_ai-agent_hierarchy-py-AgentHierarchy-get_escalation_target]]`(agent_id, task_type) → str | None` — Return the agent_id this agent should escalate task_type to, or None.
- [[eos_ai-agent_hierarchy-py-AgentHierarchy-route_request]]`(text) → str` — Determine which agent should handle a natural language request.
- [[eos_ai-agent_hierarchy-py-AgentHierarchy-format_for_prompt]]`(agent_id) → str` — Format hierarchy context for injection into an agent's system prompt.
- [[eos_ai-agent_hierarchy-py-AgentHierarchy-get_org_chart]]`() → str` — Return a human-readable org chart sorted by level.
- [[eos_ai-agent_hierarchy-py-AgentHierarchy-get_agent_config]]`(agent_id) → dict | None` — Return raw config dict for agent_id, or None if not found.
- [[eos_ai-agent_hierarchy-py-AgentHierarchy-get_agent]]`(agent_id) → dict` — Return raw config dict for agent_id, or empty dict if not found.
- [[eos_ai-agent_hierarchy-py-AgentHierarchy-list_agents]]`() → list[str]` — Return all registered agent IDs.
