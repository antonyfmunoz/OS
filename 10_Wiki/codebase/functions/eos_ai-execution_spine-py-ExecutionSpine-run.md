---
type: codebase-function
file: eos_ai/execution_spine.py
line: 29
generated: 2026-05-07
---

# ExecutionSpine.run

**File:** [[eos_ai-execution_spine-py]] | **Line:** 29
**Signature:** `run(message, unified_context, agent_type, authority_class, session_id, channel_id, org_id, user_id, task_type, venture_id, skill_name) → str`

**Class:** [[eos_ai-execution_spine-py-ExecutionSpine]]

Execute a single LLM operation with mandatory memory writes.

Returns the response string. Never raises — returns an error
message string on failure so callers always get a printable result.
