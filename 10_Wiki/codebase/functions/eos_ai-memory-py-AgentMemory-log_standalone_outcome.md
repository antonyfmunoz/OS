---
type: codebase-function
file: eos_ai/memory.py
line: 293
generated: 2026-04-12
---

# AgentMemory.log_standalone_outcome

**File:** [[eos_ai-memory-py]] | **Line:** 293
**Signature:** `log_standalone_outcome(outcome_type, score, notes, source) → str`

**Class:** [[eos_ai-memory-py-AgentMemory]]

Log an outcome with no linked interaction_id.
Used for manual /outcome Telegram commands and any event where
the originating interaction is unknown.
Returns outcome_id (UUID).

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-memory-py-AgentMemory-_fire_milestone_alert]]
