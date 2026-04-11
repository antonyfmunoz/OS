---
type: codebase-class
file: eos_ai/agent_messages.py
line: 57
generated: 2026-04-11
---

# AgentMessageBus

**File:** [[eos_ai-agent_messages-py]] | **Line:** 57

Persists agent messages to Neon events table.
Allows agents to query their inbox at runtime.

## Methods

- [[eos_ai-agent_messages-py-AgentMessageBus-__init__]]`(ctx) → None` — 
- [[eos_ai-agent_messages-py-AgentMessageBus-send]]`(message) → bool` — 
- [[eos_ai-agent_messages-py-AgentMessageBus-get_messages_for]]`(agent_id, limit) → list[dict]` — 
- [[eos_ai-agent_messages-py-AgentMessageBus-get_pending_tasks]]`(agent_id) → list[dict]` — Return unresolved task messages for this agent.
