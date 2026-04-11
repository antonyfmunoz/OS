---
type: codebase-function
file: eos_ai/memory.py
line: 468
generated: 2026-04-11
---

# AgentMemory.get_recent

**File:** [[eos_ai-memory-py]] | **Line:** 468
**Signature:** `get_recent(venture_id, limit) → list[dict]`

**Class:** [[eos_ai-memory-py-AgentMemory]]

Return recent interactions, optionally filtered by venture.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-db-py-resolve_venture]]
