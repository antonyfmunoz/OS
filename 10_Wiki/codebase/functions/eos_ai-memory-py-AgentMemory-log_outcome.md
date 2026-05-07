---
type: codebase-function
file: eos_ai/memory.py
line: 245
generated: 2026-05-07
---

# AgentMemory.log_outcome

**File:** [[eos_ai-memory-py]] | **Line:** 245
**Signature:** `log_outcome(interaction_id, outcome_type, score, notes) → str`

**Class:** [[eos_ai-memory-py-AgentMemory]]

Log an outcome against a prior interaction.
outcome_type: reply | no_reply | booked | closed | ignored
score: 1.0 = positive signal, 0.0 = negative
Returns outcome_id (UUID).

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-memory-py-AgentMemory-_fire_milestone_alert]]

## Called By

- [[services-calendly_webhook-py-_log_calendly_outcome]]
