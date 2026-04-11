---
type: codebase-function
file: eos_ai/memory.py
line: 89
generated: 2026-04-11
---

# AgentMemory.log

**File:** [[eos_ai-memory-py]] | **Line:** 89
**Signature:** `log(agent_result, venture_id, input_summary, agent, task_type, lead_username) → str`

**Class:** [[eos_ai-memory-py-AgentMemory]]

Called automatically by AgentRuntime.run(). Returns interaction_id (UUID).

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-db-py-resolve_skill]]
- [[eos_ai-db-py-resolve_venture]]
- [[eos_ai-memory-py-_tokens_to_neon]]
