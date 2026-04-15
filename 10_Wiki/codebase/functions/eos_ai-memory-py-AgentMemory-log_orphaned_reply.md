---
type: codebase-function
file: eos_ai/memory.py
line: 356
generated: 2026-04-12
---

# AgentMemory.log_orphaned_reply

**File:** [[eos_ai-memory-py]] | **Line:** 356
**Signature:** `log_orphaned_reply(username, outcome_type, score, notes) → str`

**Class:** [[eos_ai-memory-py-AgentMemory]]

Log an outcome with no matching interaction_id.
Stored in the events table for manual reconciliation.
Returns event_id (UUID).

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[services-calendly_webhook-py-_log_calendly_outcome]]
- [[services-dm_monitor-py-_log_rlhf_outcome]]
