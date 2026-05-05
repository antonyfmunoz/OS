---
type: codebase-function
file: eos_ai/memory.py
line: 429
generated: 2026-04-12
---

# AgentMemory.get_interaction_for_lead

**File:** [[eos_ai-memory-py]] | **Line:** 429
**Signature:** `get_interaction_for_lead(username, venture_id) → dict | None`

**Class:** [[eos_ai-memory-py-AgentMemory]]

Look up the most recent interaction for a lead by username.
Used by dm_monitor and calendly_webhook to resolve interaction_id.
Returns a plain dict or None if not found.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-db-py-resolve_venture]]

## Called By

- [[services-calendly_webhook-py-_log_calendly_outcome]]
- [[services-dm_monitor-py-_log_rlhf_outcome]]
- [[services-dm_monitor-py-check_inbox]]
